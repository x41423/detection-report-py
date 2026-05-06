import json
import random
import re
from pathlib import Path

from shared.project_paths import get_project_paths
DEFAULT_HISTORY_FILE = get_project_paths().history_rates_file
MAX_CHANGE_PERCENT = 5
MIN_OFFSET = 0.05
MAX_OFFSET = 0.45


class DataGeneratorService:
    """Shared pesticide data generator used by both desktop and API flows."""

    def __init__(
        self,
        high_risk=None,
        low_risk=None,
        rate_ranges=None,
        history_file=None,
    ):
        self.high_risk = list(high_risk) if high_risk else []
        self.low_risk = list(low_risk) if low_risk else []
        self.rate_ranges = dict(rate_ranges) if rate_ranges else {}
        self.history_file = Path(history_file) if history_file else DEFAULT_HISTORY_FILE
        self._original_means = {}
        for category, params in self.rate_ranges.items():
            self._original_means[category] = params.get("mean", 0)

    def configure(self, *, high_risk=None, low_risk=None, rate_ranges=None, history_file=None):
        if high_risk is not None:
            self.high_risk = list(high_risk)
        if low_risk is not None:
            self.low_risk = list(low_risk)
        if rate_ranges is not None:
            self.rate_ranges = dict(rate_ranges)
            self._original_means = {
                category: params.get("mean", 0) for category, params in self.rate_ranges.items()
            }
        if history_file is not None:
            self.history_file = Path(history_file)

    def _get_read_history_file(self) -> Path:
        if self.history_file.exists():
            return self.history_file

        default_history_file = get_project_paths().history_rates_file
        if self.history_file == default_history_file:
            legacy_history_file = get_project_paths().legacy_history_rates_file
            if legacy_history_file.exists():
                return legacy_history_file

        return self.history_file

    def load_history(self) -> dict:
        history_file = self._get_read_history_file()
        if not history_file.exists():
            return {"high": [], "low": [], "other": [], "variety_rates": {}}

        try:
            with history_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
                data.setdefault("variety_rates", {})
                return data
        except Exception:
            return {"high": [], "low": [], "other": [], "variety_rates": {}}

    def save_history(self, history: dict):
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with self.history_file.open("w", encoding="utf-8") as file:
                json.dump(history, file, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def generate_rates(self, vegs) -> list[dict]:
        history = self.load_history()
        variety_rates = history.get("variety_rates", {})
        self._calibrate_with_history(history)

        result = []
        for name in vegs:
            category, params = self._get_params(name)
            min_val = params["min"]
            max_val = params["max"]
            mean = params["mean"]
            std = params["std"]

            if name in variety_rates:
                last_rate = variety_rates[name]
                lower_bound = max(min_val, last_rate * (1 - MAX_CHANGE_PERCENT / 100))
                upper_bound = min(max_val, last_rate * (1 + MAX_CHANGE_PERCENT / 100))
                value = random.uniform(lower_bound, upper_bound)
            else:
                value = random.gauss(mean, std)
                value = max(min_val, min(max_val, value))

            value = self._avoid_integer(value)
            value = max(min_val, min(max_val, value))
            result.append({"variety": name, "rate": f"{value:.3f}%"})

            variety_rates[name] = value
            history.setdefault(category, []).append(value)
            if len(history[category]) > 1000:
                history[category] = history[category][-500:]

        history["variety_rates"] = variety_rates
        self.save_history(history)
        return result

    def _get_params(self, name):
        default_high = {"min": 20.0, "max": 60.0, "mean": 40.0, "std": 5.0}
        default_low = {"min": 0.5, "max": 15.0, "mean": 6.0, "std": 2.0}
        default_other = {"min": 5.0, "max": 40.0, "mean": 20.0, "std": 8.0}

        if any(item in name for item in self.high_risk):
            return "high", self.rate_ranges.get("high", default_high)
        if any(item in name for item in self.low_risk):
            return "low", self.rate_ranges.get("low", default_low)
        return "other", self.rate_ranges.get("other", default_other)

    def _calibrate_with_history(self, history):
        for category in ["high", "low", "other"]:
            if category in history and history[category]:
                history_avg = sum(history[category]) / len(history[category])
                if category in self.rate_ranges:
                    original_mean = self._original_means.get(category, history_avg)
                    self.rate_ranges[category]["mean"] = 0.7 * history_avg + 0.3 * original_mean

    @staticmethod
    def _avoid_integer(value):
        decimal_part = value - int(value)
        if decimal_part < 0.02 or decimal_part > 0.98:
            offset = random.uniform(MIN_OFFSET, MAX_OFFSET)
            value += offset if random.random() > 0.5 else -offset
        return value


def parse_vegetable_list(raw_text: str) -> list[str]:
    if not raw_text:
        return []

    if "," in raw_text or "\uff0c" in raw_text:
        vegs = re.split(r"[\uff0c,]+", raw_text.strip())
    else:
        vegs = raw_text.strip().split("\n")

    parsed = list(dict.fromkeys(item.strip() for item in vegs if item.strip()))
    if not parsed:
        raise ValueError("未检测到有效的蔬菜品种，请检查输入。")
    return parsed


def remove_duplicate_varieties(data: list[dict]) -> tuple[list[dict], int]:
    seen = set()
    unique = []
    for item in data:
        variety = str(item.get("variety", "")).strip()
        if variety and variety not in seen:
            seen.add(variety)
            unique.append(item)
    return unique, len(data) - len(unique)


def parse_json_data(text: str) -> list[dict]:
    data = json.loads(text.strip() or "[]")
    if not isinstance(data, list):
        raise ValueError("JSON 必须是列表格式")
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index + 1} 条记录不是对象")
        if "variety" not in item or "rate" not in item:
            raise ValueError(f"第 {index + 1} 条记录缺少 variety 或 rate 字段")
    return data


def format_json_data(data: list[dict]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
