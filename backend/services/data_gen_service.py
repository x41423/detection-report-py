"""Compatibility wrapper around the shared pesticide data module."""

from shared.pesticide_data import (
    DataGeneratorService,
    format_json_data,
    parse_json_data,
    parse_vegetable_list,
    remove_duplicate_varieties,
)

__all__ = [
    "DataGeneratorService",
    "format_json_data",
    "parse_json_data",
    "parse_vegetable_list",
    "remove_duplicate_varieties",
]
