from __future__ import annotations

import os
from dataclasses import dataclass

from app.db.veg_repository import VegRepository
from app.models.config_model import load_config
from backend.services.asr_correction_lexicon import AsrCorrectionEntry, AsrCorrectionLexicon


@dataclass(frozen=True, slots=True)
class FasterWhisperContext:
    initial_prompt: str
    hotwords: str | None
    correction_entries: list[AsrCorrectionEntry]


@dataclass(frozen=True, slots=True)
class QwenAsrContext:
    system_prompt: str
    correction_entries: list[AsrCorrectionEntry]
    domain_terms: list[str]
    correction_pairs: list[str]


class AsrContextBuilder:
    def __init__(
        self,
        *,
        lexicon: AsrCorrectionLexicon | None = None,
        use_corrections: bool | None = None,
    ) -> None:
        self.lexicon = lexicon or AsrCorrectionLexicon()
        self.use_corrections = (
            os.getenv("DAILY_INTAKE_STT_USE_ASR_CORRECTIONS", "true").strip().lower()
            not in {"0", "false", "no"}
            if use_corrections is None
            else use_corrections
        )

    def load_active_correction_entries(self) -> list[AsrCorrectionEntry]:
        if not self.use_corrections:
            return []
        return self.lexicon.load_entries(statuses={"active"})

    def build_faster_whisper_context(
        self,
        *,
        hotwords_max_count: int = 200,
        hotwords_max_chars: int = 1500,
        correction_prompt_max_pairs: int = 30,
    ) -> FasterWhisperContext:
        correction_entries = self.load_active_correction_entries()
        vocabulary = self.collect_domain_vocabulary(correction_entries=correction_entries)
        initial_prompt = (
            "这是食材点货录音。背景噪声较大时，请优先识别距离麦克风最近的人声。"
            "请输出商品名称、数量和单位。"
            "数量请优先使用阿拉伯数字，小数请使用小数点。"
            "如果听到“四点八斤”，请输出“4.8斤”，不要输出“4斤8斤”或“四斤八斤”。"
            "示例：大白菜4.8斤，土豆2.5斤，豆腐1.25包。"
        )
        correction_prompt = self.build_faster_whisper_correction_prompt(
            correction_entries,
            max_pairs=correction_prompt_max_pairs,
        )
        if correction_prompt:
            initial_prompt += correction_prompt

        hotwords = self.fit_hotwords(
            vocabulary,
            max_count=hotwords_max_count,
            max_chars=hotwords_max_chars,
        )
        return FasterWhisperContext(
            initial_prompt=initial_prompt,
            hotwords=hotwords,
            correction_entries=correction_entries,
        )

    def build_qwen_context(
        self,
        *,
        extra_context: str | None = None,
        domain_terms_limit: int = 140,
        domain_terms_max_chars: int = 1200,
        correction_pairs_limit: int = 40,
    ) -> QwenAsrContext:
        correction_entries = self.load_active_correction_entries()
        domain_terms = self.collect_domain_vocabulary(correction_entries=correction_entries)
        domain_terms = self.limit_terms(
            domain_terms,
            max_count=domain_terms_limit,
            max_chars=domain_terms_max_chars,
        )
        correction_pairs = self.collect_correction_pairs(
            correction_entries,
            max_pairs=correction_pairs_limit,
        )

        sections = [
            "This is a food inventory or daily intake audio clip. Focus on ingredient names, quantities, and units.",
            "Prefer Arabic numerals for quantities. If the speaker says a decimal quantity, keep it as a decimal number.",
        ]
        if domain_terms:
            sections.append(f"Known ingredient and unit vocabulary: {', '.join(domain_terms)}.")
        if correction_pairs:
            sections.append(f"Known correction pairs: {'; '.join(correction_pairs)}.")

        normalized_extra = str(extra_context or "").strip()
        if normalized_extra:
            sections.append(normalized_extra)

        return QwenAsrContext(
            system_prompt="\n".join(sections),
            correction_entries=correction_entries,
            domain_terms=domain_terms,
            correction_pairs=correction_pairs,
        )

    def collect_domain_vocabulary(
        self,
        *,
        correction_entries: list[AsrCorrectionEntry] | None = None,
    ) -> list[str]:
        terms: dict[str, None] = {}

        for entry in correction_entries or []:
            for value in (entry.alias, entry.canonical_name, entry.unit):
                if self.is_useful_term(value):
                    terms[value] = None

        for unit in ("斤", "公斤", "千克", "克", "包", "把", "袋", "件", "箱", "瓶", "盒", "筐"):
            if self.is_useful_term(unit):
                terms[unit] = None

        for word in ("土豆", "青椒", "茄子", "鸡腿", "鸡翅", "豆腐", "白菜", "黄瓜", "猪肉", "牛肉"):
            if self.is_useful_term(word):
                terms[word] = None

        try:
            vegetables = VegRepository.get_all_vegetables()
        except Exception:
            vegetables = []
        for item in vegetables:
            name = str(item.get("name") or "").strip()
            if self.is_useful_term(name):
                terms[name] = None

        try:
            cfg = load_config()
        except Exception:
            cfg = {}

        alias_groups = cfg.get("dish_name_aliases") or {}
        for canonical_name, aliases in alias_groups.items():
            canonical = str(canonical_name or "").strip()
            if self.is_useful_term(canonical):
                terms[canonical] = None
            for alias in aliases or []:
                alias_name = str(alias or "").strip()
                if self.is_useful_term(alias_name):
                    terms[alias_name] = None

        return list(terms.keys())

    def collect_correction_pairs(
        self,
        correction_entries: list[AsrCorrectionEntry],
        *,
        max_pairs: int,
    ) -> list[str]:
        pairs: list[str] = []
        seen: set[str] = set()
        for entry in correction_entries:
            alias = entry.alias.strip()
            canonical = entry.canonical_name.strip()
            unit = entry.unit.strip()
            if not alias or not canonical:
                continue
            pair = f"{alias} -> {canonical}"
            if unit:
                pair += f" ({unit})"
            key = pair.lower()
            if key in seen:
                continue
            seen.add(key)
            pairs.append(pair)
            if len(pairs) >= max_pairs:
                break
        return pairs

    def build_faster_whisper_correction_prompt(
        self,
        correction_entries: list[AsrCorrectionEntry],
        *,
        max_pairs: int,
    ) -> str:
        pairs: list[str] = []
        for entry in correction_entries[:max_pairs]:
            if entry.alias.lower() == entry.canonical_name.lower():
                pairs.append(f"{entry.canonical_name}常用单位{entry.unit}")
            else:
                pairs.append(f"{entry.alias}应识别为{entry.canonical_name}，常用单位{entry.unit}")
        if not pairs:
            return ""
        return "已确认易错词：" + "；".join(pairs) + "。"

    def fit_hotwords(self, terms: list[str], *, max_count: int, max_chars: int) -> str | None:
        selected_words: list[str] = []
        used_chars = 0
        for word in terms[:max_count]:
            extra = len(word) + (1 if selected_words else 0)
            if used_chars + extra > max_chars:
                break
            selected_words.append(word)
            used_chars += extra
        return ",".join(selected_words) if selected_words else None

    def limit_terms(self, terms: list[str], *, max_count: int, max_chars: int) -> list[str]:
        selected: list[str] = []
        used_chars = 0
        for term in terms:
            extra_chars = len(term) + (2 if selected else 0)
            if len(selected) >= max_count or used_chars + extra_chars > max_chars:
                break
            selected.append(term)
            used_chars += extra_chars
        return selected

    def is_useful_term(self, value: str) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        if len(text) > 12:
            return False
        if any(marker in text.lower() for marker in ("history", "test", "demo")):
            return False
        if any(marker in text for marker in ("_", "/", "\\")):
            return False
        return True
