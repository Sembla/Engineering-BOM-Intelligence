from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.generate_demo_evidence import generate_evidence


class DemoEvidenceTests(unittest.TestCase):
    def test_generated_evidence_is_synthetic_and_traceable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            report = generate_evidence(output_dir)

            self.assertEqual(
                report["data_classification"],
                "synthetic_public_demo",
            )
            self.assertEqual(report["processing"], "deterministic")
            self.assertEqual(report["metrics"]["source_rows"], 12)
            self.assertEqual(report["metrics"]["distinct_codes"], 12)
            self.assertTrue((output_dir / "normalized-demo-bom.csv").is_file())
            self.assertTrue((output_dir / "validation-report.json").is_file())
            self.assertTrue((output_dir / "demo-summary.svg").is_file())

    def test_generated_evidence_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            generate_evidence(Path(first))
            generate_evidence(Path(second))

            for filename in (
                "normalized-demo-bom.csv",
                "validation-report.json",
                "demo-summary.svg",
            ):
                self.assertEqual(
                    (Path(first) / filename).read_bytes(),
                    (Path(second) / filename).read_bytes(),
                )


if __name__ == "__main__":
    unittest.main()
