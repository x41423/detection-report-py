import unittest

from app.utils.weekly_price_update import (
    _build_suggested_match,
    _normalize_alias_map,
    _resolve_target_path,
    build_name_candidates,
)


class WeeklyPriceHelperTests(unittest.TestCase):
    def test_build_name_candidates_splits_alias_variants(self):
        self.assertEqual(
            build_name_candidates("alpha/beta/gamma"),
            ["alpha/beta/gamma", "alpha", "beta", "gamma", "alphabetagamma"],
        )

    def test_normalize_alias_map_discards_blank_items(self):
        alias_map = _normalize_alias_map(
            {
                " alpha/beta ": " alpha beta target ",
                "": "invalid",
                "blank target": " ",
            }
        )
        self.assertEqual(alias_map, {"alpha/beta": "alpha beta target"})

    def test_resolve_target_path_falls_back_from_xls(self):
        target_path, warning = _resolve_target_path(r"C:\demo\quote.xls")
        self.assertEqual(target_path, r"C:\demo\quote_weekly_updated.xlsx")
        self.assertIn(".xls", warning)

    def test_resolve_target_path_keeps_explicit_xlsx_path(self):
        target_path, warning = _resolve_target_path(
            r"C:\demo\source.xlsx",
            r"D:\exports\custom-output.xlsx",
        )
        self.assertEqual(target_path, r"D:\exports\custom-output.xlsx")
        self.assertEqual(warning, "")

    def test_resolve_target_path_converts_explicit_xlsm_path(self):
        target_path, warning = _resolve_target_path(
            r"C:\demo\source.xlsx",
            r"D:\exports\custom-output.xlsm",
        )
        self.assertEqual(target_path, r"D:\exports\custom-output.xlsx")
        self.assertIn(".xlsm", warning)

    def test_build_suggested_match_preselects_clear_best_candidate(self):
        reference_entries = [
            type(
                "Entry",
                (),
                {
                    "display_name": "alphabeta-target",
                    "candidates": tuple(build_name_candidates("alphabeta-target")),
                },
            )(),
            type(
                "Entry",
                (),
                {
                    "display_name": "other-target",
                    "candidates": tuple(build_name_candidates("other-target")),
                },
            )(),
        ]

        result = _build_suggested_match("alpha/beta", reference_entries)

        self.assertEqual(result["source_name"], "alpha/beta")
        self.assertEqual(result["preselected_target_name"], "alphabeta-target")
        self.assertTrue(result["candidates"])


if __name__ == "__main__":
    unittest.main()
