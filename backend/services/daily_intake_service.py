from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.db.daily_intake_repository import DailyIntakeRepository
from app.db.store import init_database
from app.db.veg_repository import VegRepository
from app.models.config_model import load_config


class DailyIntakeService:
    CATEGORY_VALUES = {'vegetable', 'frozen', 'meat'}
    UNIT_ALIASES = {
        '斤': '斤', '金': '斤', '今': '斤', '井': '斤', '近': '斤',
        '公斤': '公斤', '千克': '公斤', 'kg': '公斤', 'KG': '公斤', 'Kg': '公斤',
        '包': '包', '个': '个', '条': '条', '箱': '箱',
        '筐': '筐', '框': '筐', '袋': '袋', '把': '把',
        '瓶': '瓶', '板': '板', '版': '板', '桶': '桶',
        '罐': '罐', '盒': '盒', '块': '块',
        '升': '升', 'L': '升', 'l': '升',
        '克': '克', 'g': '克',
    }
    COMMON_NAME_CORRECTIONS = {
        '香姑': '香菇', '相菇': '香菇', '香茹': '香菇',
        '蘑姑': '蘑菇', '模菇': '蘑菇', '磨菇': '蘑菇', '膜菇': '蘑菇',
        '平菇': '蘑菇', '评估': '蘑菇',
        '青交': '青椒', '青焦': '青椒', '青校': '青椒',
        '大白才': '大白菜', '大白菜': '大白菜',
        '豆付': '豆腐', '豆付皮': '豆腐皮', '豆皮': '豆腐皮',
        '连藕': '莲藕', '联藕': '莲藕', '藕': '莲藕',
        '酸豆脚': '酸豆角',
        '鸡间': '鸡尖', '鸡件': '鸡尖',
        '生将': '生姜', '声姜': '生姜',
        '山要': '山药',
        '西勤': '西芹', '小西琴': '小西芹',
        '算台': '蒜苔', '算苔': '蒜苔',
    }
    FROZEN_KEYWORDS = ('冻', '冷冻', '冰鲜')
    MEAT_KEYWORDS = (
        '鸡', '鸭', '鹅', '猪', '牛', '羊', '肉', '鱼', '虾',
        '排骨', '鸡腿', '鸡翅', '里脊', '五花',
    )
    _QUANTITY_TOKEN = '[0-9零一二两三四五六七八九十百千万点\\.]+'
    _UNIT_PATTERN = '公斤|千克|kg|KG|Kg|斤|金|今|井|近|包|个|条|箱|筐|框|袋|把|瓶|板|版|桶|罐|盒|块|升|L|l|克|g'

    def __init__(self) -> None:
        init_database()

    # ------------------------------------------------------------------
    # Sheet queries
    # ------------------------------------------------------------------
    def get_today_sheet(self) -> dict[str, Any]:
        return self.get_sheet(date.today().isoformat())

    def get_sheet(self, intake_date: str) -> dict[str, Any]:
        normalized_date = self._normalize_intake_date(intake_date)
        sheet = DailyIntakeRepository.get_sheet_by_date(
            normalized_date,
            create_if_missing=True,
        )
        return {
            'success': True,
            'message': f'已加载 {normalized_date} 的点货单',
            'sheet': self._serialize_sheet(sheet),
        }

    def list_history(self, limit: int = 30) -> dict[str, Any]:
        if limit <= 0:
            raise ValueError('history limit 必须大于 0')
        sheets = [
            self._serialize_history_entry(sheet)
            for sheet in DailyIntakeRepository.list_history(limit=min(limit, 365))
        ]
        return {
            'success': True,
            'message': f'已加载最近 {len(sheets)} 份点货历史',
            'sheets': sheets,
            'total': len(sheets),
        }

    # ------------------------------------------------------------------
    # Item mutations
    # ------------------------------------------------------------------
    def add_item(
        self,
        intake_date: str,
        name: str,
        category: str,
        quantity: float,
        unit: str,
        source: str = 'manual',
        transcript: str = '',
    ) -> dict[str, Any]:
        payload = self._prepare_item_payload(
            intake_date=intake_date,
            name=name,
            category=category,
            quantity=quantity,
            unit=unit,
            source=source,
            transcript=transcript,
        )
        result = DailyIntakeRepository.add_or_merge_item(**payload)
        return self._build_item_mutation_response(
            result=result,
            created_message='条目已新增',
            merged_message='已累计到现有条目',
        )

    def update_item(
        self,
        item_id: int,
        name: str,
        category: str,
        quantity: float,
        unit: str,
        source: str = 'manual',
        transcript: str = '',
    ) -> dict[str, Any]:
        if item_id <= 0:
            raise ValueError('item_id 必须是正整数')
        payload = self._prepare_item_payload(
            name=name,
            category=category,
            quantity=quantity,
            unit=unit,
            source=source,
            transcript=transcript,
        )
        result = DailyIntakeRepository.update_item(item_id=item_id, **payload)
        return self._build_item_mutation_response(
            result=result,
            created_message='条目已更新',
            merged_message='编辑后已并入现有条目',
        )

    def delete_item(self, item_id: int) -> dict[str, Any]:
        if item_id <= 0:
            raise ValueError('item_id 必须是正整数')
        result = DailyIntakeRepository.delete_item(item_id)
        return {
            'success': True,
            'message': '条目已删除',
            'sheet': self._serialize_sheet(result['sheet']),
        }

    # ------------------------------------------------------------------
    # Voice transcript parsing
    # ------------------------------------------------------------------
    def parse_transcript(
        self,
        transcript: str,
        intake_date: str,
        category: str | None = None,
    ) -> dict[str, Any]:
        normalized_date = self._normalize_intake_date(intake_date)
        raw_transcript = str(transcript or '').strip()
        explicit_category = self._normalize_category(category) if category else None

        if not raw_transcript:
            return self._build_parse_response(
                raw_transcript=raw_transcript,
                parse_status='invalid',
                warnings=['未识别到语音内容'],
                message='未识别到语音内容，请重试或手动录入',
                category_hint=explicit_category,
            )

        compact = self._compact_transcript(raw_transcript)

        success_match = re.fullmatch(
            f'(?P<name>.+?)(?P<quantity>{self._QUANTITY_TOKEN})(?P<unit>{self._UNIT_PATTERN})',
            compact,
            flags=re.IGNORECASE,
        )
        if success_match:
            return self._parse_success_match(
                intake_date=normalized_date,
                raw_transcript=raw_transcript,
                match=success_match,
                explicit_category=explicit_category,
            )

        quantity_only_match = re.fullmatch(
            f'(?P<name>.+?)(?P<quantity>{self._QUANTITY_TOKEN})',
            compact,
        )
        if quantity_only_match:
            draft_name = self._clean_name(quantity_only_match.group('name'))
            quantity = self._parse_quantity(quantity_only_match.group('quantity'))
            return self._build_parse_response(
                raw_transcript=raw_transcript,
                draft_name=draft_name or None,
                normalized_name=self._normalize_name(draft_name)[0] if draft_name else None,
                quantity=quantity,
                parse_status='invalid',
                warnings=['缺少单位，请手动确认'],
                message='语音里缺少单位，请补充后再保存',
                category_hint=self._infer_category(draft_name, explicit_category) if draft_name else explicit_category,
            )

        unit_only_match = re.fullmatch(
            f'(?P<name>.+?)(?P<unit>{self._UNIT_PATTERN})',
            compact,
            flags=re.IGNORECASE,
        )
        if unit_only_match:
            draft_name = self._clean_name(unit_only_match.group('name'))
            return self._build_parse_response(
                raw_transcript=raw_transcript,
                draft_name=draft_name or None,
                normalized_name=self._normalize_name(draft_name)[0] if draft_name else None,
                unit=self._normalize_unit(unit_only_match.group('unit')),
                parse_status='invalid',
                warnings=['缺少数量，请手动确认'],
                message='语音里缺少数量，请补充后再保存',
                category_hint=self._infer_category(draft_name, explicit_category) if draft_name else explicit_category,
            )

        return self._build_parse_response(
            raw_transcript=raw_transcript,
            parse_status='invalid',
            warnings=['无法按“菜名 + 数量 + 单位”的规则解析'],
            message='无法解析这条语音，请改用手动录入或重新说一遍',
            category_hint=explicit_category,
        )

    def normalize_inventory_item(self, name: str, unit: str) -> dict[str, Any]:
        raw_name = self._clean_name(name)
        if not raw_name:
            raise ValueError('商品名称不能为空')
        normalized_name, veg_id = self._normalize_name(raw_name)
        unit_name = self._normalize_unit(unit)
        return {
            'display_name': raw_name,
            'normalized_name': normalized_name,
            'veg_id': veg_id,
            'unit_name': unit_name,
        }

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    def _parse_success_match(
        self,
        *,
        intake_date: str,
        raw_transcript: str,
        match,
        explicit_category: str | None,
    ) -> dict[str, Any]:
        draft_name = self._clean_name(match.group('name'))
        if not draft_name:
            return self._build_parse_response(
                raw_transcript=raw_transcript,
                parse_status='invalid',
                warnings=['缺少商品名称'],
                message='语音里缺少商品名称，请重试',
                category_hint=explicit_category,
            )

        quantity = self._parse_quantity(match.group('quantity'))
        if quantity is None or quantity <= 0:
            return self._build_parse_response(
                raw_transcript=raw_transcript,
                draft_name=draft_name,
                parse_status='invalid',
                warnings=['数量无法识别'],
                message='数量无法识别，请手动修正后保存',
                category_hint=explicit_category,
            )

        normalized_name, _ = self._normalize_name(draft_name)
        unit_name = self._normalize_unit(match.group('unit'))
        category_hint = self._infer_category(normalized_name, explicit_category)

        merge_preview = self._build_merge_preview(
            intake_date=intake_date,
            normalized_name=normalized_name,
            unit_name=unit_name,
            quantity=quantity,
        )

        message = '已解析语音草稿，请确认后保存'
        if merge_preview:
            message = '已识别到重复条目，保存后会自动累计数量'

        return self._build_parse_response(
            raw_transcript=raw_transcript,
            draft_name=draft_name,
            normalized_name=normalized_name,
            quantity=quantity,
            unit=unit_name,
            category_hint=category_hint,
            parse_status='parsed',
            warnings=[],
            message=message,
            merge_preview=merge_preview,
        )

    def _build_merge_preview(
        self,
        *,
        intake_date: str,
        normalized_name: str,
        unit_name: str,
        quantity: float,
    ) -> dict[str, Any] | None:
        candidate = DailyIntakeRepository.find_merge_candidate(
            intake_date=intake_date,
            normalized_name=normalized_name,
            unit_name=unit_name,
        )
        if not candidate:
            return None

        current_quantity = float(candidate['quantity'])
        return {
            'item_id': int(candidate['id']),
            'current_quantity': current_quantity,
            'next_quantity': current_quantity + float(quantity),
            'unit_name': candidate['unit_name'],
            'merge_count': int(candidate['merge_count']),
        }

    # ------------------------------------------------------------------
    # Normalisation helpers
    # ------------------------------------------------------------------
    def _prepare_item_payload(
        self,
        *,
        intake_date: str | None = None,
        name: str,
        category: str,
        quantity: float,
        unit: str,
        source: str | None,
        transcript: str | None,
    ) -> dict[str, Any]:
        raw_name = self._clean_name(name)
        if not raw_name:
            raise ValueError('商品名称不能为空')
        normalized_name, veg_id = self._normalize_name(raw_name)
        normalized_category = self._normalize_category(category)
        normalized_unit = self._normalize_unit(unit)
        normalized_source = self._normalize_source(source)

        try:
            numeric_quantity = float(quantity)
        except (TypeError, ValueError) as exc:
            raise ValueError('数量必须是数字') from exc
        if numeric_quantity <= 0:
            raise ValueError('数量必须大于 0')

        payload: dict[str, Any] = {
            'raw_name': raw_name,
            'normalized_name': normalized_name,
            'category': normalized_category,
            'unit_name': normalized_unit,
            'quantity': numeric_quantity,
            'source': normalized_source,
            'transcript': str(transcript or '').strip(),
            'last_confirmed_at': self._now_string(),
            'veg_id': veg_id,
        }
        if intake_date is not None:
            payload['intake_date'] = self._normalize_intake_date(intake_date)
        return payload

    def _normalize_name(self, name: str) -> tuple[str, int | None]:
        cleaned = self._clean_name(name)
        cleaned = self._resolve_alias_name(cleaned)
        veg = VegRepository.get_vegetable_by_name(cleaned)
        if veg:
            return str(veg['name']), int(veg['id'])
        return cleaned, None

    def _resolve_alias_name(self, name: str) -> str:
        cleaned = self._clean_name(name)
        if not cleaned:
            return cleaned
        corrected = self.COMMON_NAME_CORRECTIONS.get(cleaned)
        if corrected:
            return corrected

        try:
            cfg = load_config()
            alias_groups = cfg.get('dish_name_aliases') or {}
            alias_lookup: dict[str, str] = {}
            for canonical_name, aliases in alias_groups.items():
                canonical = self._clean_name(canonical_name)
                if not canonical:
                    continue
                alias_lookup[canonical] = canonical
                for alias in aliases or []:
                    alias_name = self._clean_name(alias)
                    if not alias_name:
                        continue
                    alias_lookup[alias_name] = canonical
            return alias_lookup.get(cleaned, cleaned)
        except Exception:
            return cleaned

    def _normalize_unit(self, unit: str) -> str:
        candidate = str(unit or '').strip()
        if not candidate:
            raise ValueError('单位不能为空')
        normalized = self.UNIT_ALIASES.get(candidate)
        if not normalized:
            raise ValueError(f'不支持的单位: {candidate}')
        return normalized

    def _normalize_category(self, category: str) -> str:
        candidate = str(category or '').strip().lower()
        if candidate not in self.CATEGORY_VALUES:
            raise ValueError(f'不支持的分类: {category}')
        return candidate

    def _normalize_source(self, source: str | None) -> str:
        candidate = str(source or '').strip().lower() or 'manual'
        if candidate not in frozenset({'voice', 'manual'}):
            raise ValueError(f'不支持的录入来源: {source}')
        return candidate

    def _normalize_intake_date(self, intake_date: str) -> str:
        try:
            return date.fromisoformat(str(intake_date)).isoformat()
        except ValueError as exc:
            raise ValueError('intake_date 必须是 YYYY-MM-DD 格式') from exc

    def _infer_category(self, name: str, explicit_category: str | None) -> str:
        if explicit_category:
            return explicit_category
        if any(keyword in name for keyword in self.FROZEN_KEYWORDS):
            return 'frozen'
        if any(keyword in name for keyword in self.MEAT_KEYWORDS):
            return 'meat'
        return 'vegetable'

    def _compact_transcript(self, transcript: str) -> str:
        return re.sub(r'[\s,，、。；;]+', '', transcript).strip()

    def _clean_name(self, name: str) -> str:
        cleaned = re.sub(r'^[,，、。；;]+|[,，、。；;]+$', '', str(name or '').strip())
        return re.sub(r'\s+', '', cleaned)

    def _parse_quantity(self, token: str) -> float | None:
        value = str(token or '').strip()
        if not value:
            return None
        if re.fullmatch(r'\d+(?:\.\d+)?', value):
            return float(value)

        normalized = value.replace('两', '二')
        if '点' in normalized:
            integer_part, decimal_part = normalized.split('点', 1)
            integer_value = (
                self._parse_chinese_integer(integer_part) if integer_part else 0
            )
            decimal_digits: list[str] = []
            for char in decimal_part:
                if char not in self._chinese_digits():
                    return None
                decimal_digits.append(str(self._chinese_digits()[char]))
            if integer_value is None or not decimal_digits:
                return None
            return float(f"{integer_value}.{''.join(decimal_digits)}")

        integer_value = self._parse_chinese_integer(normalized)
        if integer_value is None:
            return None
        return float(integer_value)

    def _parse_chinese_integer(self, token: str) -> int | None:
        digits = self._chinese_digits()
        units = {'十': 10, '百': 100, '千': 1000, '万': 10000}
        total = 0
        section = 0
        number = 0
        for char in token:
            if char in digits:
                number = digits[char]
                continue
            if char not in units:
                return None
            unit_value = units[char]
            if unit_value == 10000:
                section = (section + number) * unit_value
                total += section
                section = 0
                number = 0
            else:
                section += (number or 1) * unit_value
                number = 0
        return total + section + number

    # ------------------------------------------------------------------
    # Response builders
    # ------------------------------------------------------------------
    def _build_item_mutation_response(
        self,
        *,
        result: dict[str, Any],
        created_message: str,
        merged_message: str,
    ) -> dict[str, Any]:
        sheet = self._serialize_sheet(result['sheet'])
        merged = bool(result['merged'])
        return {
            'success': True,
            'message': merged_message if merged else created_message,
            'item': self._find_serialized_item(sheet, int(result['item_id'])),
            'sheet': sheet,
            'merged': merged,
        }

    def _build_parse_response(self, **payload) -> dict[str, Any]:
        parse_status = payload.get('parse_status', 'invalid')
        payload.setdefault('success', parse_status == 'parsed')
        payload.setdefault('message', '语音已处理')
        payload.setdefault('requires_confirmation', True)
        payload.setdefault('warnings', [])
        payload.setdefault('merge_preview', None)
        return payload

    def _serialize_sheet(self, sheet: dict[str, Any] | None) -> dict[str, Any]:
        if not sheet:
            raise KeyError('未找到对应的点货单')
        return {
            'id': int(sheet['id']),
            'intake_date': sheet['intake_date'],
            'status': sheet['status'],
            'created_at': sheet['created_at'],
            'updated_at': sheet['updated_at'],
            'item_count': int(sheet.get('item_count', 0)),
            'total_quantity': round(float(sheet.get('total_quantity', 0)), 2),
            'quantity_by_unit': sheet.get('quantity_by_unit', {}),
            'category_counts': sheet.get('category_counts', {}),
            'items': [self._serialize_item(item) for item in sheet.get('items', [])],
        }

    def _serialize_history_entry(self, sheet: dict[str, Any]) -> dict[str, Any]:
        return {
            'id': int(sheet['id']),
            'intake_date': sheet['intake_date'],
            'status': sheet['status'],
            'created_at': sheet['created_at'],
            'updated_at': sheet['updated_at'],
            'item_count': int(sheet.get('item_count', 0)),
            'total_quantity': round(float(sheet.get('total_quantity', 0)), 2),
        }

    def _serialize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            'id': int(item['id']),
            'sheet_id': int(item['sheet_id']),
            'veg_id': item['veg_id'],
            'raw_name': item['raw_name'],
            'normalized_name': item['normalized_name'],
            'category': item['category'],
            'quantity': float(item['quantity']),
            'source': item['source'],
            'transcript': item.get('transcript') or '',
            'last_source': item['last_source'],
            'last_transcript': item.get('last_transcript') or '',
            'merge_count': int(item['merge_count']),
            'last_confirmed_at': item.get('last_confirmed_at'),
            'created_at': item.get('created_at'),
            'updated_at': item.get('updated_at'),
            'unit_id': int(item['unit_id']),
            'unit_name': item['unit_name'],
        }

    def _find_serialized_item(
        self,
        sheet: dict[str, Any],
        item_id: int,
    ) -> dict[str, Any] | None:
        for item in sheet['items']:
            if int(item['id']) == item_id:
                return item
        return None

    def _now_string(self) -> str:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def _chinese_digits() -> dict[str, int]:
        return {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        }
