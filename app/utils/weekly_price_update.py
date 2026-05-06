import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

READABLE_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}
WRITABLE_EXTENSION = ".xlsx"
NAME_SPLIT_RE = re.compile(r"[/／、，,；;|\n]+")
HEADER_KEYWORDS = (
    "报价",
    "模板",
    "执行价",
    "食材名称",
    "名称",
    "品牌",
    "规格",
    "单位",
)
NAME_COLUMN_KEYWORDS = ("名称", "菜名", "品名", "食材", "商品", "name")
PRICE_COLUMN_KEYWORDS = ("价", "价格", "单价", "报价", "执行价", "参考价", "金额", "price")
MAX_SUGGESTIONS = 3
MIN_SUGGESTION_SCORE = 0.52
PRESELECT_MIN_SCORE = 0.78
PRESELECT_GAP = 0.08
CONTAINMENT_BONUS = 0.08
TOKEN_OVERLAP_BONUS = 0.04

LEGACY_WEEKLY_PRICE_ALIASES = {
    "沙葛/豆薯/凉薯": "沙葛豆薯地瓜",
    "本地油菜花菜心": "本地油菜菜心",
    "水面筋（凉皮用）": "水发面筋（凉皮用）",
    "萧山散装萝卜干": "散装萝卜干",
    "散装泡发绿海带丝": "绿海带丝",
    "散装盐渍绿海带丝": "绿海带丝",
}


@dataclass(frozen=True)
class ReferenceEntry:
    display_name: str
    normalized_name: str
    price: float
    candidates: tuple[str, ...]


def get_default_weekly_price_aliases() -> dict[str, str]:
    return dict(LEGACY_WEEKLY_PRICE_ALIASES)


def normalize_name(name: Any) -> str:
    if name is None or pd.isna(name):
        return ""

    text = "".join(str(name).strip().lower().split())
    if text in {"", "nan", "none"}:
        return ""
    return text


def display_name(name: Any) -> str:
    if name is None or pd.isna(name):
        return ""

    text = re.sub(r"\s+", " ", str(name)).strip()
    if text.lower() in {"", "nan", "none"}:
        return ""
    return text


def build_name_candidates(name: Any) -> list[str]:
    pretty_name = display_name(name)
    normalized_name = normalize_name(name)
    if not pretty_name or not normalized_name:
        return []

    candidates = [normalized_name]
    split_candidates = [
        normalize_name(part)
        for part in NAME_SPLIT_RE.split(pretty_name)
        if normalize_name(part)
    ]
    candidates.extend(split_candidates)

    if len(split_candidates) > 1:
        merged_candidate = "".join(split_candidates)
        if merged_candidate:
            candidates.append(merged_candidate)

    return _dedupe_candidates(candidates)


def preview_weekly_prices(
    update_path: str,
    reference_path: str,
    weekly_price_aliases: dict[str, str] | None = None,
    update_name_col: int = 1,
    update_price_col: int = 6,
    ref_name_col: int = 0,
    ref_price_col: int = 1,
    data_start_row: int | None = None,
    update_start_row: int | None = None,
    reference_start_row: int | None = None,
) -> dict[str, Any]:
    (
        analysis,
        _,
        _,
    ) = _analyze_weekly_prices(
        update_path=update_path,
        reference_path=reference_path,
        weekly_price_aliases=weekly_price_aliases,
        update_name_col=update_name_col,
        update_price_col=update_price_col,
        ref_name_col=ref_name_col,
        ref_price_col=ref_price_col,
        data_start_row=data_start_row,
        update_start_row=update_start_row,
        reference_start_row=reference_start_row,
    )
    return analysis


def update_weekly_prices(
    update_path: str,
    reference_path: str,
    output_path: str | None = None,
    weekly_price_aliases: dict[str, str] | None = None,
    update_name_col: int = 1,
    update_price_col: int = 6,
    ref_name_col: int = 0,
    ref_price_col: int = 1,
    data_start_row: int | None = None,
    update_start_row: int | None = None,
    reference_start_row: int | None = None,
) -> dict[str, Any]:
    analysis, update_df, row_updates = _analyze_weekly_prices(
        update_path=update_path,
        reference_path=reference_path,
        weekly_price_aliases=weekly_price_aliases,
        update_name_col=update_name_col,
        update_price_col=update_price_col,
        ref_name_col=ref_name_col,
        ref_price_col=ref_price_col,
        data_start_row=data_start_row,
        update_start_row=update_start_row,
        reference_start_row=reference_start_row,
    )

    target_path, warning = _resolve_target_path(update_path, output_path)

    backup_path = None
    if os.path.abspath(target_path) == os.path.abspath(update_path):
        backup_path, warning = _try_backup_source(update_path, warning)

    if row_updates:
        price_col_idx = row_updates[0][1]
        col_label = update_df.columns[price_col_idx]
        update_df[col_label] = update_df[col_label].astype(object)
    for row_index, price_col, new_price in row_updates:
        update_df.iloc[row_index, price_col] = new_price

    target_path, warning = _write_excel_with_fallback(
        update_df=update_df,
        target_path=target_path,
        warning=warning,
    )

    analysis["output_path"] = target_path
    analysis["backup_path"] = backup_path
    analysis["warning"] = warning
    return analysis


def _analyze_weekly_prices(
    update_path: str,
    reference_path: str,
    weekly_price_aliases: dict[str, str] | None,
    update_name_col: int,
    update_price_col: int,
    ref_name_col: int,
    ref_price_col: int,
    data_start_row: int | None,
    update_start_row: int | None,
    reference_start_row: int | None,
) -> tuple[dict[str, Any], pd.DataFrame, list[tuple[int, int, float]]]:
    if not update_path or not os.path.exists(update_path):
        raise FileNotFoundError(f"待更新报价表不存在: {update_path}")
    if not reference_path or not os.path.exists(reference_path):
        raise FileNotFoundError(f"参考报价表不存在: {reference_path}")

    update_df = _read_excel(update_path)
    reference_df = _read_excel(reference_path)
    column_warnings: list[str] = []
    update_name_col, update_price_col, update_column_warnings = _resolve_table_columns(
        update_df,
        requested_name_col=update_name_col,
        requested_price_col=update_price_col,
        table_label="待更新报价表",
    )
    ref_name_col, ref_price_col, reference_column_warnings = _resolve_table_columns(
        reference_df,
        requested_name_col=ref_name_col,
        requested_price_col=ref_price_col,
        table_label="参考报价表",
    )
    column_warnings.extend(update_column_warnings)
    column_warnings.extend(reference_column_warnings)

    if update_start_row is None:
        update_start_row = data_start_row
    if update_start_row is None:
        update_start_row = _detect_data_start_row(update_df, update_name_col, update_price_col)
    if reference_start_row is None:
        reference_start_row = _detect_data_start_row(reference_df, ref_name_col, ref_price_col)

    reference_entries, reference_candidate_map = _build_reference_index(
        ref_df=reference_df,
        reference_start_row=reference_start_row,
        ref_name_col=ref_name_col,
        ref_price_col=ref_price_col,
    )
    alias_map = _normalize_alias_map(weekly_price_aliases)

    matched_items: list[dict[str, Any]] = []
    row_updates: list[tuple[int, int, float]] = []
    not_matched_rows: list[str] = []
    warnings: list[str] = list(column_warnings)
    warning_set: set[str] = set(column_warnings)
    alias_hit_count = 0

    for row_index in range(update_start_row, len(update_df)):
        raw_name = update_df.iloc[row_index, update_name_col]
        source_name = display_name(raw_name)
        source_candidates = build_name_candidates(raw_name)
        if not source_name or not source_candidates:
            continue

        direct_entry = _match_reference_entry(source_candidates, reference_candidate_map)
        if direct_entry is not None:
            new_price = direct_entry.price
            old_price = _coerce_price(update_df.iloc[row_index, update_price_col])
            matched_items.append(
                {
                    "name": source_name,
                    "old_price": old_price,
                    "new_price": new_price,
                    "changed": old_price != new_price,
                    "match_type": "exact",
                }
            )
            row_updates.append((row_index, update_price_col, new_price))
            continue

        alias_target = alias_map.get(normalize_name(source_name))
        if alias_target:
            alias_entry = _match_reference_entry(
                build_name_candidates(alias_target),
                reference_candidate_map,
            )
            if alias_entry is not None:
                new_price = alias_entry.price
                old_price = _coerce_price(update_df.iloc[row_index, update_price_col])
                matched_items.append(
                    {
                        "name": source_name,
                        "old_price": old_price,
                        "new_price": new_price,
                        "changed": old_price != new_price,
                        "match_type": "alias",
                    }
                )
                row_updates.append((row_index, update_price_col, new_price))
                alias_hit_count += 1
                continue

            warning = f"已保存别名“{source_name} -> {alias_target}”在当前参考表中找不到目标菜名，本次未应用。"
            if warning not in warning_set:
                warnings.append(warning)
                warning_set.add(warning)

        not_matched_rows.append(source_name)

    unique_not_matched = list(dict.fromkeys(not_matched_rows))
    suggested_matches = [
        _build_suggested_match(source_name, reference_entries)
        for source_name in unique_not_matched
    ]

    analysis = {
        "matched_count": len(matched_items),
        "updated_count": len(matched_items),
        "matched_items": matched_items,
        "not_matched": unique_not_matched,
        "not_matched_count": len(not_matched_rows),
        "not_matched_unique_count": len(unique_not_matched),
        "suggested_matches": suggested_matches,
        "alias_hit_count": alias_hit_count,
        "warnings": warnings,
        "update_start_row": update_start_row,
        "reference_start_row": reference_start_row,
    }
    return analysis, update_df, row_updates


def _resolve_table_columns(
    df: pd.DataFrame,
    *,
    requested_name_col: int,
    requested_price_col: int,
    table_label: str,
) -> tuple[int, int, list[str]]:
    """Validate requested column indices and return resolved (name_col, price_col, warnings).

    Strategy:
    1. If the requested column is in-range AND its header cell matches the expected keywords,
       use it as-is (the caller's default is already correct).
    2. Only fall back to keyword auto-detection when the requested column header does NOT
       match, which catches cases where the file layout differs from the default assumption.
    """
    warnings: list[str] = []
    num_cols = len(df.columns)

    name_col = requested_name_col
    price_col = requested_price_col

    if name_col < 0 or name_col >= num_cols:
        warnings.append(f"{table_label}: 名称列索引 {name_col} 超出范围（共 {num_cols} 列），已回退到第 0 列。")
        name_col = 0
    if price_col < 0 or price_col >= num_cols:
        warnings.append(f"{table_label}: 价格列索引 {price_col} 超出范围（共 {num_cols} 列），已回退到最后一列。")
        price_col = num_cols - 1

    if not _column_matches_keywords(df, name_col, NAME_COLUMN_KEYWORDS):
        detected = _detect_column_by_keywords(df, NAME_COLUMN_KEYWORDS)
        if detected is not None and detected != name_col:
            warnings.append(
                f"{table_label}: 名称列默认在第 {name_col + 1} 列，但该列表头不含名称关键词，"
                f"已自动切换到第 {detected + 1} 列。"
            )
            name_col = detected

    if not _column_matches_keywords(df, price_col, PRICE_COLUMN_KEYWORDS):
        detected = _detect_column_by_keywords(df, PRICE_COLUMN_KEYWORDS)
        if detected is not None and detected != price_col:
            warnings.append(
                f"{table_label}: 价格列默认在第 {price_col + 1} 列，但该列表头不含价格关键词，"
                f"已自动切换到第 {detected + 1} 列。"
            )
            price_col = detected

    return name_col, price_col, warnings


def _column_matches_keywords(df: pd.DataFrame, col_index: int, keywords: tuple[str, ...]) -> bool:
    """Return True if any cell in the given column (rows 1-10) contains a keyword.
    Row 0 is skipped because it is typically a file title row."""
    preview_rows = min(len(df), 10)
    for row_index in range(1, preview_rows):
        cell = display_name(df.iloc[row_index, col_index])
        if cell and any(kw in cell for kw in keywords):
            return True
    return False


def _detect_column_by_keywords(df: pd.DataFrame, keywords: tuple[str, ...]) -> int | None:
    """Scan rows 1-10 for a column whose header cell contains one of the keywords.
    Row 0 is skipped because it is typically a file title row."""
    preview_rows = min(len(df), 10)
    num_cols = len(df.columns)

    for row_index in range(1, preview_rows):
        for col_index in range(num_cols):
            cell = display_name(df.iloc[row_index, col_index])
            if cell and any(kw in cell for kw in keywords):
                return col_index
    return None


def _read_excel(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext not in READABLE_EXTENSIONS:
        readable = ", ".join(sorted(READABLE_EXTENSIONS))
        raise ValueError(f"仅支持读取这些 Excel 格式: {readable}")

    if ext == ".xls":
        try:
            return pd.read_excel(path, header=None, engine="xlrd")
        except ImportError as exc:
            raise ValueError("当前环境缺少 .xls 读取支持，请改用 .xlsx 文件") from exc

    return pd.read_excel(path, header=None, engine="openpyxl")


def _detect_data_start_row(df: pd.DataFrame, name_col: int, price_col: int) -> int:
    preview_rows = min(len(df), 12)
    for row_index in range(preview_rows):
        raw_name = df.iloc[row_index, name_col]
        raw_price = df.iloc[row_index, price_col]

        if not display_name(raw_name):
            continue
        if _looks_like_header(raw_name, raw_price):
            continue
        return row_index
    return 0


def _looks_like_header(raw_name: Any, raw_price: Any) -> bool:
    header_text = f"{display_name(raw_name)} {display_name(raw_price)}".strip()
    if not header_text:
        return False
    return any(keyword in header_text for keyword in HEADER_KEYWORDS)


def _build_reference_index(
    ref_df: pd.DataFrame,
    reference_start_row: int,
    ref_name_col: int,
    ref_price_col: int,
) -> tuple[list[ReferenceEntry], dict[str, ReferenceEntry]]:
    entries: list[ReferenceEntry] = []
    candidate_map: dict[str, ReferenceEntry] = {}

    for row_index in range(reference_start_row, len(ref_df)):
        raw_name = ref_df.iloc[row_index, ref_name_col]
        source_name = display_name(raw_name)
        if not source_name:
            continue

        price = _coerce_price(ref_df.iloc[row_index, ref_price_col])
        if price is None:
            continue

        candidates = tuple(build_name_candidates(source_name))
        if not candidates:
            continue

        entry = ReferenceEntry(
            display_name=source_name,
            normalized_name=normalize_name(source_name),
            price=price,
            candidates=candidates,
        )
        entries.append(entry)
        for candidate in entry.candidates:
            candidate_map.setdefault(candidate, entry)

    return entries, candidate_map


def _normalize_alias_map(weekly_price_aliases: dict[str, str] | None) -> dict[str, str]:
    normalized_aliases: dict[str, str] = {}
    for source_name, target_name in (weekly_price_aliases or {}).items():
        source_display = display_name(source_name)
        target_display = display_name(target_name)
        if not source_display or not target_display:
            continue
        normalized_aliases[normalize_name(source_display)] = target_display
    return normalized_aliases


def _match_reference_entry(
    name_candidates: list[str],
    reference_candidate_map: dict[str, ReferenceEntry],
) -> ReferenceEntry | None:
    for candidate in name_candidates:
        entry = reference_candidate_map.get(candidate)
        if entry is not None:
            return entry
    return None


def _build_suggested_match(source_name: str, reference_entries: list[ReferenceEntry]) -> dict[str, Any]:
    source_candidates = build_name_candidates(source_name)
    scored_candidates: list[dict[str, Any]] = []

    for entry in reference_entries:
        score = _score_reference_candidate(source_candidates, entry.candidates)
        if score < MIN_SUGGESTION_SCORE:
            continue
        scored_candidates.append(
            {
                "target_name": entry.display_name,
                "score": round(score, 3),
            }
        )

    scored_candidates.sort(key=lambda item: (-item["score"], item["target_name"]))
    top_candidates = scored_candidates[:MAX_SUGGESTIONS]

    preselected_target_name = None
    if top_candidates:
        top_score = top_candidates[0]["score"]
        next_score = top_candidates[1]["score"] if len(top_candidates) > 1 else 0.0
        if top_score >= PRESELECT_MIN_SCORE and top_score - next_score >= PRESELECT_GAP:
            preselected_target_name = top_candidates[0]["target_name"]

    return {
        "source_name": source_name,
        "candidates": top_candidates,
        "preselected_target_name": preselected_target_name,
    }


def _score_reference_candidate(source_candidates: list[str], target_candidates: tuple[str, ...]) -> float:
    best_score = 0.0

    for source_candidate in source_candidates:
        for target_candidate in target_candidates:
            score = SequenceMatcher(None, source_candidate, target_candidate).ratio()
            if source_candidate in target_candidate or target_candidate in source_candidate:
                score += CONTAINMENT_BONUS
            best_score = max(best_score, min(score, 1.0))

    source_tokens = {token for token in source_candidates if len(token) >= 2}
    target_tokens = {token for token in target_candidates if len(token) >= 2}
    if source_tokens & target_tokens:
        best_score = min(best_score + TOKEN_OVERLAP_BONUS, 1.0)

    return best_score


def _dedupe_candidates(candidates: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
    return deduped


def _coerce_price(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_target_path(update_path: str, output_path: str | None = None) -> tuple[str, str]:
    requested_path = output_path or update_path
    ext = os.path.splitext(requested_path)[1].lower()

    if ext == WRITABLE_EXTENSION:
        return requested_path, ""

    if ext == ".xls":
        base = os.path.splitext(requested_path)[0]
        if os.path.abspath(requested_path) == os.path.abspath(update_path):
            target = f"{base}_weekly_updated{WRITABLE_EXTENSION}"
        else:
            target = f"{base}{WRITABLE_EXTENSION}"
        warning = "当前环境不支持写出 .xls，结果已自动另存为 .xlsx"
        return target, warning

    if ext == ".xlsm":
        base = os.path.splitext(requested_path)[0]
        if os.path.abspath(requested_path) == os.path.abspath(update_path):
            target = f"{base}_weekly_updated{WRITABLE_EXTENSION}"
        else:
            target = f"{base}{WRITABLE_EXTENSION}"
        warning = "当前环境不会保留 .xlsm 宏，结果已自动另存为 .xlsx"
        return target, warning

    raise ValueError("仅支持输出 .xlsx 文件")


def _write_excel_with_fallback(update_df: pd.DataFrame, target_path: str, warning: str) -> tuple[str, str]:
    try:
        update_df.to_excel(target_path, index=False, header=False, engine="openpyxl")
        return target_path, warning
    except (PermissionError, OSError):
        attempted_paths = [target_path]
        for fallback_path in _build_permission_fallback_paths(target_path):
            try:
                update_df.to_excel(fallback_path, index=False, header=False, engine="openpyxl")
                if os.path.dirname(fallback_path) == os.path.dirname(target_path):
                    fallback_warning = f"原目标文件无法写入，结果已自动另存为 {os.path.basename(fallback_path)}"
                else:
                    fallback_warning = f"目标目录无法写入，结果已自动保存到临时目录: {fallback_path}"
                warning = f"{warning}。{fallback_warning}" if warning else fallback_warning
                return fallback_path, warning
            except (PermissionError, OSError):
                attempted_paths.append(fallback_path)

        attempted = " | ".join(attempted_paths)
        raise PermissionError(f"无法写入 Excel 文件。已尝试这些路径但都失败了: {attempted}")


def _build_permission_fallback_path(directory: str, target_path: str) -> str:
    stem = os.path.splitext(os.path.basename(target_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(directory, f"{stem}_autosave_{timestamp}{WRITABLE_EXTENSION}")


def _build_permission_fallback_paths(target_path: str) -> list[str]:
    original_dir = os.path.dirname(target_path)
    temp_dir = tempfile.gettempdir()

    paths = [_build_permission_fallback_path(original_dir, target_path)]
    if os.path.abspath(temp_dir) != os.path.abspath(original_dir):
        paths.append(_build_permission_fallback_path(temp_dir, target_path))
    return paths


def _try_backup_source(update_path: str, warning: str) -> tuple[str | None, str]:
    backup_path = update_path + ".bak"
    try:
        shutil.copy2(update_path, backup_path)
        return backup_path, warning
    except (PermissionError, OSError):
        backup_warning = "原文件备份未创建，程序将继续直接处理当前文件"
        warning = f"{warning}。{backup_warning}" if warning else backup_warning
        return None, warning
