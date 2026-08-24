"""Deterministic BOM calculations independent from the Streamlit interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


REQUIRED_COLUMNS = {
    "item",
    "family",
    "component_type",
    "width_mm",
    "height_mm",
    "length_mm",
    "quantity",
    "material",
    "measure_basis",
    "unit_cost",
    "waste_pct",
}

NUMERIC_COLUMNS = {
    "width_mm",
    "height_mm",
    "length_mm",
    "quantity",
    "unit_cost",
    "waste_pct",
}

SUPPORTED_BASES = {"area_m2", "linear_m", "unit"}


@dataclass(frozen=True)
class BomMetrics:
    estimated_cost: float
    component_units: float
    distinct_materials: int
    source_rows: int


def validate_bom(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize a BOM input table.

    Raises:
        ValueError: when required columns, values or measurement bases are invalid.
    """
    missing = sorted(REQUIRED_COLUMNS.difference(dataframe.columns))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    normalized = dataframe.copy()
    for column in NUMERIC_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    invalid_numeric = sorted(
        column for column in NUMERIC_COLUMNS if normalized[column].isna().any()
    )
    if invalid_numeric:
        raise ValueError("Non-numeric or empty values in: " + ", ".join(invalid_numeric))

    if (normalized["quantity"] <= 0).any():
        raise ValueError("quantity must be greater than zero")
    if (normalized[["width_mm", "height_mm", "length_mm", "unit_cost", "waste_pct"]] < 0).any().any():
        raise ValueError("dimensions, costs and waste percentages cannot be negative")

    normalized["measure_basis"] = normalized["measure_basis"].astype(str).str.strip().str.lower()
    invalid_bases = sorted(set(normalized["measure_basis"]) - SUPPORTED_BASES)
    if invalid_bases:
        raise ValueError("Unsupported measure_basis values: " + ", ".join(invalid_bases))

    missing_area = (normalized["measure_basis"] == "area_m2") & (
        (normalized["width_mm"] <= 0) | (normalized["height_mm"] <= 0)
    )
    if missing_area.any():
        raise ValueError("area_m2 rows require width_mm and height_mm greater than zero")

    missing_length = (normalized["measure_basis"] == "linear_m") & (
        normalized["length_mm"] <= 0
    )
    if missing_length.any():
        raise ValueError("linear_m rows require length_mm greater than zero")

    return normalized


def _base_measure(row: pd.Series) -> float:
    if row["measure_basis"] == "area_m2":
        return float(row["width_mm"] * row["height_mm"] / 1_000_000)
    if row["measure_basis"] == "linear_m":
        return float(row["length_mm"] / 1_000)
    return 1.0


def calculate_bom(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Calculate consumption and estimated cost for each BOM row."""
    calculated = validate_bom(dataframe)
    calculated["base_measure_per_unit"] = calculated.apply(_base_measure, axis=1)
    calculated["net_measure"] = calculated["base_measure_per_unit"] * calculated["quantity"]
    calculated["purchase_measure"] = calculated["net_measure"] * (
        1 + calculated["waste_pct"] / 100
    )
    calculated["estimated_cost"] = calculated["purchase_measure"] * calculated["unit_cost"]
    return calculated


def summarize_materials(calculated: pd.DataFrame) -> pd.DataFrame:
    """Aggregate estimated consumption and cost by material and basis."""
    return (
        calculated.groupby(["material", "measure_basis"], dropna=False)[
            ["quantity", "purchase_measure", "estimated_cost"]
        ]
        .sum()
        .reset_index()
        .sort_values("estimated_cost", ascending=False)
    )


def calculate_metrics(calculated: pd.DataFrame) -> BomMetrics:
    return BomMetrics(
        estimated_cost=float(calculated["estimated_cost"].sum()),
        component_units=float(calculated["quantity"].sum()),
        distinct_materials=int(calculated["material"].nunique()),
        source_rows=int(len(calculated)),
    )


def optimization_notes(calculated: pd.DataFrame) -> list[str]:
    """Return transparent rule-based observations, not AI recommendations."""
    notes: list[str] = []

    high_waste = calculated[calculated["waste_pct"] > 5]
    if not high_waste.empty:
        notes.append(
            f"{len(high_waste)} row(s) use waste above 5%; review cutting plans and assumptions."
        )

    top_cost = calculated.nlargest(min(3, len(calculated)), "estimated_cost")
    if not top_cost.empty:
        names = ", ".join(top_cost["item"].astype(str))
        notes.append(f"Highest estimated cost contribution: {names}.")

    if calculated["material"].nunique() > 4:
        notes.append("More than four materials are present; review purchasing complexity.")

    zero_cost = calculated[calculated["unit_cost"] == 0]
    if not zero_cost.empty:
        notes.append(f"{len(zero_cost)} row(s) have zero unit cost and require price validation.")

    return notes or ["No rule-based review flags were triggered for this dataset."]


def required_columns() -> Iterable[str]:
    return sorted(REQUIRED_COLUMNS)
