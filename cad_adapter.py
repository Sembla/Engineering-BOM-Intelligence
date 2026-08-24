"""Neutral adapter for BOM tables exported from CAD workflows.

The public schema is intentionally independent from any employer, customer or
production system. Private field mappings belong outside this repository.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

import pandas as pd


REQUIRED_CAD_FIELDS = {"code", "component", "quantity"}

PUBLIC_COLUMN_ALIASES = {
    "row_id": "source_row",
    "item_id": "code",
    "item_description": "component",
    "quantity": "quantity",
    "dimension_x_mm": "dimension_x_mm",
    "dimension_y_mm": "dimension_y_mm",
    "dimension_z_mm": "dimension_z_mm",
    "finish_primary": "primary_finish",
    "finish_secondary": "secondary_finish",
}

FINISH_FIELDS = ("primary_finish", "secondary_finish")


@dataclass(frozen=True)
class CadQualityMetrics:
    source_rows: int
    component_units: float
    distinct_codes: int
    distinct_components: int
    dimension_coverage_pct: float
    finish_coverage_pct: float
    review_rows: int


def _slug(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _column_map(dataframe: pd.DataFrame) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for source_column in dataframe.columns:
        canonical = PUBLIC_COLUMN_ALIASES.get(_slug(source_column))
        if canonical and canonical not in mapped:
            mapped[canonical] = str(source_column)
    return mapped


def is_cad_export(dataframe: pd.DataFrame) -> bool:
    """Return True when the table follows the neutral public CAD schema."""
    return REQUIRED_CAD_FIELDS.issubset(_column_map(dataframe))


def _text_series(dataframe: pd.DataFrame, source: str | None) -> pd.Series:
    if source is None:
        return pd.Series("", index=dataframe.index, dtype="string")
    return dataframe[source].fillna("").astype("string").str.strip()


def _numeric_series(
    dataframe: pd.DataFrame,
    source: str | None,
    label: str,
    *,
    required: bool = False,
) -> pd.Series:
    if source is None:
        if required:
            raise ValueError(f"Missing required public column: {label}")
        return pd.Series(0.0, index=dataframe.index, dtype="float64")

    raw = (
        dataframe[source]
        .fillna("")
        .astype("string")
        .str.strip()
        .str.replace(",", ".", regex=False)
    )
    converted = pd.to_numeric(raw.replace("", pd.NA), errors="coerce")
    invalid = raw.ne("") & converted.isna()
    if invalid.any():
        rows = ", ".join(str(index + 2) for index in dataframe.index[invalid][:5])
        raise ValueError(f"Invalid numeric value in {label}; check CSV row(s): {rows}")
    if required and converted.isna().any():
        rows = ", ".join(str(index + 2) for index in dataframe.index[converted.isna()][:5])
        raise ValueError(f"Empty value in required column {label}; check CSV row(s): {rows}")
    return converted.fillna(0.0).astype("float64")


def normalize_cad_export(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Convert the neutral public CAD schema to the engine data contract."""
    columns = _column_map(dataframe)
    missing = sorted(REQUIRED_CAD_FIELDS.difference(columns))
    if missing:
        raise ValueError("Missing required public CAD fields: " + ", ".join(missing))

    component = _text_series(dataframe, columns.get("component"))
    code = _text_series(dataframe, columns.get("code"))
    quantity = _numeric_series(
        dataframe, columns.get("quantity"), "quantity", required=True
    )
    if component.eq("").any():
        raise ValueError("item descriptions cannot be empty")
    if code.eq("").any():
        raise ValueError("public item identifiers cannot be empty")
    if (quantity <= 0).any():
        raise ValueError("quantity must be greater than zero")

    source_row = _numeric_series(dataframe, columns.get("source_row"), "row_id")
    if columns.get("source_row") is None:
        source_row = pd.Series(
            range(1, len(dataframe) + 1), index=dataframe.index, dtype="float64"
        )

    normalized = pd.DataFrame(index=dataframe.index)
    normalized["source_row"] = source_row.astype("int64")
    normalized["cad_code"] = code
    normalized["item"] = component
    normalized["family"] = "PUBLIC_DEMO"
    normalized["component_type"] = "UNCLASSIFIED"
    normalized["width_mm"] = _numeric_series(
        dataframe, columns.get("dimension_x_mm"), "dimension_x_mm"
    )
    normalized["height_mm"] = _numeric_series(
        dataframe, columns.get("dimension_y_mm"), "dimension_y_mm"
    )
    normalized["length_mm"] = _numeric_series(
        dataframe, columns.get("dimension_z_mm"), "dimension_z_mm"
    )
    normalized["quantity"] = quantity

    for finish_field in FINISH_FIELDS:
        normalized[finish_field] = _text_series(dataframe, columns.get(finish_field))

    finish_present = normalized[list(FINISH_FIELDS)].ne("").any(axis=1)
    normalized["material"] = "UNSPECIFIED"
    normalized.loc[finish_present, "material"] = "FINISH_SPECIFIED"
    normalized["measure_basis"] = "unit"
    normalized["unit_cost"] = 0.0
    normalized["waste_pct"] = 0.0

    dimension_count = normalized[["width_mm", "height_mm", "length_mm"]].gt(0).sum(axis=1)
    normalized["attribute_completeness_pct"] = (
        (2 + dimension_count + finish_present.astype(int)) / 6 * 100
    ).round(1)
    normalized["review_status"] = "READY"
    normalized.loc[dimension_count.eq(0), "review_status"] = "CHECK_DIMENSIONS"
    return normalized.reset_index(drop=True)


def cad_quality_metrics(normalized: pd.DataFrame) -> CadQualityMetrics:
    rows = len(normalized)
    dimension_present = normalized[["width_mm", "height_mm", "length_mm"]].gt(0).any(axis=1)
    finish_present = normalized[list(FINISH_FIELDS)].ne("").any(axis=1)
    return CadQualityMetrics(
        source_rows=rows,
        component_units=float(normalized["quantity"].sum()),
        distinct_codes=int(normalized["cad_code"].nunique()),
        distinct_components=int(normalized["item"].nunique()),
        dimension_coverage_pct=round(float(dimension_present.mean() * 100), 1) if rows else 0.0,
        finish_coverage_pct=round(float(finish_present.mean() * 100), 1) if rows else 0.0,
        review_rows=int(normalized["review_status"].ne("READY").sum()),
    )


def cad_review_flags(normalized: pd.DataFrame) -> list[str]:
    notes: list[str] = []
    missing_dimensions = normalized["review_status"].eq("CHECK_DIMENSIONS").sum()
    if missing_dimensions:
        notes.append(f"{missing_dimensions} row(s) have no dimensional attribute.")

    missing_finishes = normalized[list(FINISH_FIELDS)].eq("").all(axis=1).sum()
    if missing_finishes:
        notes.append(f"{missing_finishes} row(s) have no finish attribute.")

    descriptions_per_code = normalized.groupby("cad_code")["item"].nunique()
    multi_description_codes = int(descriptions_per_code.gt(1).sum())
    if multi_description_codes:
        notes.append(
            f"{multi_description_codes} item identifier(s) map to multiple descriptions."
        )

    duplicate_rows = normalized.duplicated(
        subset=["cad_code", "item", "width_mm", "height_mm", "length_mm"]
    ).sum()
    if duplicate_rows:
        notes.append(f"{duplicate_rows} repeated line(s) may be candidates for consolidation.")

    return notes or ["No deterministic data-quality flags were triggered."]
