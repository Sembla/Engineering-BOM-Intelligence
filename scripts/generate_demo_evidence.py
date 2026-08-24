from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cad_adapter import (
    cad_quality_metrics,
    cad_review_flags,
    normalize_cad_export,
)


SAMPLE_PATH = ROOT / "data" / "sample_cad_bom.csv"
DEFAULT_OUTPUT_DIR = ROOT / "docs" / "evidence"


def _metric_card(x: int, label: str, value: str, accent: str) -> str:
    return f"""
    <rect x="{x}" y="225" width="285" height="150" rx="18"
          fill="#0f1728" stroke="#24324a" stroke-width="2"/>
    <rect x="{x}" y="225" width="8" height="150" rx="4" fill="{accent}"/>
    <text x="{x + 30}" y="275" class="metric-label">{escape(label)}</text>
    <text x="{x + 30}" y="335" class="metric-value">{escape(value)}</text>
    """


def _coverage_bar(y: int, label: str, value: float, accent: str) -> str:
    width = round(740 * max(0.0, min(value, 100.0)) / 100)
    return f"""
    <text x="100" y="{y}" class="bar-label">{escape(label)}</text>
    <text x="1245" y="{y}" class="bar-value">{value:.1f}%</text>
    <rect x="390" y="{y - 22}" width="740" height="28" rx="14" fill="#18243a"/>
    <rect x="390" y="{y - 22}" width="{width}" height="28" rx="14" fill="{accent}"/>
    """


def _build_svg(report: dict[str, object]) -> str:
    metrics = report["metrics"]
    flags = report["review_flags"]
    flag_text = " | ".join(str(flag) for flag in flags)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="800"
viewBox="0 0 1440 800" role="img"
aria-label="Engineering BOM Intelligence reproducible synthetic demo snapshot">
  <defs>
    <linearGradient id="background" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="#050914"/>
      <stop offset="100%" stop-color="#0a1630"/>
    </linearGradient>
    <style>
      .title {{ fill: #ffffff; font: 700 42px Arial, sans-serif; }}
      .subtitle {{ fill: #aebbd0; font: 400 22px Arial, sans-serif; }}
      .eyebrow {{ fill: #c6ff00; font: 700 17px Arial, sans-serif; letter-spacing: 3px; }}
      .metric-label {{ fill: #9fb0c8; font: 600 19px Arial, sans-serif; }}
      .metric-value {{ fill: #ffffff; font: 700 46px Arial, sans-serif; }}
      .section {{ fill: #ffffff; font: 700 26px Arial, sans-serif; }}
      .bar-label {{ fill: #cbd5e1; font: 600 20px Arial, sans-serif; }}
      .bar-value {{ fill: #ffffff; font: 700 20px Arial, sans-serif; text-anchor: end; }}
      .note {{ fill: #9fb0c8; font: 400 17px Arial, sans-serif; }}
      .footer {{ fill: #dbe5f4; font: 600 17px Arial, sans-serif; }}
    </style>
  </defs>

  <rect width="1440" height="800" fill="url(#background)"/>
  <path d="M0 0 H1440 V8 H0 Z" fill="#0057ff"/>
  <path d="M0 8 H520 V14 H0 Z" fill="#c6ff00"/>

  <text x="90" y="82" class="eyebrow">REPRODUCIBLE PUBLIC EVIDENCE</text>
  <text x="90" y="137" class="title">Engineering BOM Intelligence</text>
  <text x="90" y="178" class="subtitle">
    Deterministic validation of a neutral, fictional CAD-style BOM
  </text>

  {_metric_card(90, "BOM rows", str(metrics["source_rows"]), "#c6ff00")}
  {_metric_card(390, "Component units", f'{metrics["component_units"]:,.0f}', "#0057ff")}
  {_metric_card(690, "Distinct public codes", str(metrics["distinct_codes"]), "#c6ff00")}
  {_metric_card(990, "Rows for review", str(metrics["review_rows"]), "#0057ff")}

  <text x="90" y="440" class="section">Data-quality coverage</text>
  {_coverage_bar(505, "Dimensions", float(metrics["dimension_coverage_pct"]), "#0057ff")}
  {_coverage_bar(570, "Finishes", float(metrics["finish_coverage_pct"]), "#c6ff00")}

  <rect x="90" y="625" width="1175" height="68" rx="14"
        fill="#0f1728" stroke="#24324a" stroke-width="2"/>
  <text x="115" y="653" class="note">Deterministic review flags</text>
  <text x="115" y="679" class="footer">{escape(flag_text)}</text>

  <text x="90" y="750" class="footer">
    Synthetic public data • deterministic processing • normalized CSV export • UI smoke tests
  </text>
  <text x="1350" y="750" class="note" text-anchor="end">
    No employer or client data
  </text>
</svg>
"""


def generate_evidence(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    source = pd.read_csv(SAMPLE_PATH)
    normalized = normalize_cad_export(source)
    quality = cad_quality_metrics(normalized)
    report: dict[str, object] = {
        "source": "data/sample_cad_bom.csv",
        "data_classification": "synthetic_public_demo",
        "processing": "deterministic",
        "metrics": {
            "source_rows": quality.source_rows,
            "component_units": quality.component_units,
            "distinct_codes": quality.distinct_codes,
            "distinct_components": quality.distinct_components,
            "dimension_coverage_pct": quality.dimension_coverage_pct,
            "finish_coverage_pct": quality.finish_coverage_pct,
            "review_rows": quality.review_rows,
        },
        "review_flags": cad_review_flags(normalized),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(
        output_dir / "normalized-demo-bom.csv",
        index=False,
        encoding="utf-8",
        lineterminator="\n",
    )
    (output_dir / "validation-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    clean_svg = "\n".join(
        line.rstrip() for line in _build_svg(report).splitlines()
    ) + "\n"
    (output_dir / "demo-summary.svg").write_text(clean_svg, encoding="utf-8")
    return report


if __name__ == "__main__":
    generate_evidence()
