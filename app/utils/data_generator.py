"""Legacy desktop-facing helpers backed by the shared pesticide data module."""

from pathlib import Path

from shared.pesticide_data import (
    DEFAULT_HISTORY_FILE,
    DataGeneratorService,
    format_json_data,
    parse_json_data,
    parse_vegetable_list,
    remove_duplicate_varieties,
)


HISTORY_FILE = str(DEFAULT_HISTORY_FILE)
_generator = DataGeneratorService(history_file=Path(HISTORY_FILE))


def _refresh_generator():
    global _generator
    _generator.configure(history_file=Path(HISTORY_FILE))


def load_history() -> dict:
    _refresh_generator()
    return _generator.load_history()


def save_history(history: dict):
    _refresh_generator()
    _generator.save_history(history)


def calibrate_ranges_with_history():
    _refresh_generator()
    _generator._calibrate_with_history(_generator.load_history())


def set_risk_lists(high_risk: list[str], low_risk: list[str]):
    _generator.configure(high_risk=high_risk, low_risk=low_risk)


def set_rate_ranges(ranges: dict):
    _generator.configure(rate_ranges=ranges)


def gen_inhibition_rates(vegs: list[str]) -> list[dict]:
    _refresh_generator()
    return _generator.generate_rates(vegs)


__all__ = [
    "HISTORY_FILE",
    "calibrate_ranges_with_history",
    "format_json_data",
    "gen_inhibition_rates",
    "load_history",
    "parse_json_data",
    "parse_vegetable_list",
    "remove_duplicate_varieties",
    "save_history",
    "set_rate_ranges",
    "set_risk_lists",
]
