from __future__ import annotations

import unittest

import pandas as pd

from bom_engine import (
    calculate_bom,
    calculate_metrics,
    optimization_notes,
    summarize_materials,
    validate_bom,
)


def sample_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "item": "PANEL",
                "family": "DISPLAY",
                "component_type": "PANEL",
                "width_mm": 1000,
                "height_mm": 2000,
                "length_mm": 0,
                "quantity": 2,
                "material": "MDP",
                "measure_basis": "area_m2",
                "unit_cost": 100,
                "waste_pct": 5,
            },
            {
                "item": "PROFILE",
                "family": "DISPLAY",
                "component_type": "PROFILE",
                "width_mm": 0,
                "height_mm": 0,
                "length_mm": 1000,
                "quantity": 3,
                "material": "PVC",
                "measure_basis": "linear_m",
                "unit_cost": 10,
                "waste_pct": 0,
            },
            {
                "item": "FOOT",
                "family": "HARDWARE",
                "component_type": "HARDWARE",
                "width_mm": 0,
                "height_mm": 0,
                "length_mm": 0,
                "quantity": 4,
                "material": "STEEL",
                "measure_basis": "unit",
                "unit_cost": 5,
                "waste_pct": 0,
            },
        ]
    )


class BomEngineTests(unittest.TestCase):
    def test_calculates_area_linear_and_unit_costs(self) -> None:
        result = calculate_bom(sample_dataframe())
        self.assertAlmostEqual(result.iloc[0]["estimated_cost"], 420.0)
        self.assertAlmostEqual(result.iloc[1]["estimated_cost"], 30.0)
        self.assertAlmostEqual(result.iloc[2]["estimated_cost"], 20.0)

    def test_metrics_are_consistent(self) -> None:
        metrics = calculate_metrics(calculate_bom(sample_dataframe()))
        self.assertAlmostEqual(metrics.estimated_cost, 470.0)
        self.assertEqual(metrics.component_units, 9)
        self.assertEqual(metrics.distinct_materials, 3)

    def test_summary_preserves_measurement_basis(self) -> None:
        summary = summarize_materials(calculate_bom(sample_dataframe()))
        self.assertEqual(set(summary["measure_basis"]), {"area_m2", "linear_m", "unit"})

    def test_rejects_missing_columns(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            validate_bom(pd.DataFrame({"item": ["PANEL"]}))

    def test_rejects_invalid_measurement_basis(self) -> None:
        data = sample_dataframe()
        data.loc[0, "measure_basis"] = "kg"
        with self.assertRaisesRegex(ValueError, "Unsupported measure_basis"):
            validate_bom(data)

    def test_rejects_non_positive_quantity(self) -> None:
        data = sample_dataframe()
        data.loc[0, "quantity"] = 0
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            validate_bom(data)

    def test_notes_identify_zero_cost(self) -> None:
        data = sample_dataframe()
        data.loc[0, "unit_cost"] = 0
        notes = optimization_notes(calculate_bom(data))
        self.assertTrue(any("zero unit cost" in note for note in notes))


if __name__ == "__main__":
    unittest.main()
