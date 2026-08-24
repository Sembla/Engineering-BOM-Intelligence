from __future__ import annotations

import unittest

import pandas as pd

from cad_adapter import (
    cad_quality_metrics,
    cad_review_flags,
    is_cad_export,
    normalize_cad_export,
)


def cad_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "row_id": 1,
                "item_id": "ITEM-001",
                "item_description": "COMPONENT-01",
                "quantity": 2,
                "dimension_x_mm": 900,
                "dimension_y_mm": 2000,
                "dimension_z_mm": 350,
                "finish_primary": "FINISH-A",
            },
            {
                "row_id": 2,
                "item_id": "ITEM-002",
                "item_description": "COMPONENT-02",
                "quantity": 6,
                "dimension_x_mm": "",
                "dimension_y_mm": "",
                "dimension_z_mm": "",
                "finish_primary": "",
            },
        ]
    )


class CadAdapterTests(unittest.TestCase):
    def test_detects_neutral_public_cad_schema(self) -> None:
        self.assertTrue(is_cad_export(cad_dataframe()))
        self.assertFalse(is_cad_export(pd.DataFrame({"item": ["A"]})))

    def test_normalizes_export_to_engine_contract(self) -> None:
        result = normalize_cad_export(cad_dataframe())
        self.assertEqual(result.loc[0, "item"], "COMPONENT-01")
        self.assertEqual(result.loc[0, "width_mm"], 900)
        self.assertEqual(result.loc[0, "height_mm"], 2000)
        self.assertEqual(result.loc[0, "length_mm"], 350)
        self.assertEqual(result.loc[0, "measure_basis"], "unit")
        self.assertEqual(result.loc[0, "component_type"], "UNCLASSIFIED")

    def test_quality_metrics_are_traceable(self) -> None:
        metrics = cad_quality_metrics(normalize_cad_export(cad_dataframe()))
        self.assertEqual(metrics.source_rows, 2)
        self.assertEqual(metrics.component_units, 8)
        self.assertEqual(metrics.distinct_codes, 2)
        self.assertEqual(metrics.dimension_coverage_pct, 50.0)
        self.assertEqual(metrics.finish_coverage_pct, 50.0)
        self.assertEqual(metrics.review_rows, 1)

    def test_rejects_invalid_quantity(self) -> None:
        data = cad_dataframe()
        data["quantity"] = data["quantity"].astype("object")
        data.loc[0, "quantity"] = "not-a-number"
        with self.assertRaisesRegex(ValueError, "Invalid numeric value"):
            normalize_cad_export(data)

    def test_flags_missing_dimensions_and_finishes(self) -> None:
        notes = cad_review_flags(normalize_cad_export(cad_dataframe()))
        self.assertTrue(any("dimensional attribute" in note for note in notes))
        self.assertTrue(any("finish attribute" in note for note in notes))


if __name__ == "__main__":
    unittest.main()
