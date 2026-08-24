from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class AppSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = AppTest.from_file(
            str(ROOT / "app.py"),
            default_timeout=30,
        ).run()

    def test_synthetic_demo_loads_without_runtime_errors(self) -> None:
        self.assertEqual(list(self.app.exception), [])
        self.assertEqual(self.app.title[0].value, "Engineering BOM Intelligence")
        self.assertIn("Demo mode", self.app.caption[1].value)

    def test_demo_exposes_traceable_metrics_and_review_tabs(self) -> None:
        labels = [metric.label for metric in self.app.metric]
        self.assertEqual(
            labels,
            [
                "BOM rows",
                "Component units",
                "Distinct CAD codes",
                "Dimension coverage",
            ],
        )
        self.assertEqual(
            [tab.label for tab in self.app.tabs],
            [
                "CAD source",
                "Normalized BOM",
                "Component summary",
                "Data quality",
            ],
        )
        self.assertGreaterEqual(len(self.app.dataframe), 3)


if __name__ == "__main__":
    unittest.main()
