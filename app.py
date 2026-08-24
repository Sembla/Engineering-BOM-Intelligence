from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from bom_engine import (
    calculate_bom,
    calculate_metrics,
    optimization_notes,
    summarize_materials,
)
from cad_adapter import (
    cad_quality_metrics,
    cad_review_flags,
    is_cad_export,
    normalize_cad_export,
)


SAMPLE_PATH = Path(__file__).parent / "data" / "sample_cad_bom.csv"

st.set_page_config(page_title="Engineering BOM Intelligence", layout="wide")
st.title("Engineering BOM Intelligence")
st.caption("CAD BOM normalization, validation, quality review and deterministic calculations")


def load_source(uploaded_file: object | None) -> tuple[pd.DataFrame, bool]:
    if uploaded_file is None:
        return pd.read_csv(SAMPLE_PATH), True
    name = str(getattr(uploaded_file, "name", "")).lower()
    if name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file), False
    return pd.read_csv(uploaded_file), False


st.info(
    "Use the bundled synthetic CAD sample or upload a CSV/XLSX file. Processing is "
    "deterministic and uploaded data is not persisted by this prototype."
)

uploaded = st.file_uploader("Upload a CAD or normalized BOM", type=["csv", "xlsx"])
source, using_sample = load_source(uploaded)
if using_sample:
    st.caption("Demo mode: using a neutral synthetic CAD-style BOM with fictional data.")

try:
    cad_mode = is_cad_export(source)
    normalized = normalize_cad_export(source) if cad_mode else source
    calculated = calculate_bom(normalized)
except (ValueError, OSError, pd.errors.ParserError) as error:
    st.error(f"Input validation failed: {error}")
    st.stop()

if cad_mode:
    quality = cad_quality_metrics(normalized)
    metric_rows, metric_units, metric_codes, metric_coverage = st.columns(4)
    metric_rows.metric("BOM rows", quality.source_rows)
    metric_units.metric("Component units", f"{quality.component_units:,.0f}")
    metric_codes.metric("Distinct CAD codes", quality.distinct_codes)
    metric_coverage.metric("Dimension coverage", f"{quality.dimension_coverage_pct:.1f}%")

    source_tab, normalized_tab, summary_tab, review_tab = st.tabs(
        ["CAD source", "Normalized BOM", "Component summary", "Data quality"]
    )
    with source_tab:
        st.dataframe(source, width="stretch")
    with normalized_tab:
        st.dataframe(normalized, width="stretch")
    with summary_tab:
        summary = (
            normalized.groupby(["component_type", "material"], dropna=False)
            .agg(line_items=("item", "size"), component_units=("quantity", "sum"))
            .reset_index()
            .sort_values("component_units", ascending=False)
        )
        st.dataframe(summary, width="stretch")
    with review_tab:
        st.write(f"Finish coverage: {quality.finish_coverage_pct:.1f}%")
        st.write(f"Rows requiring dimension review: {quality.review_rows}")
        for note in cad_review_flags(normalized):
            st.write(f"- {note}")

    csv_output = normalized.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download normalized BOM",
        data=csv_output,
        file_name="normalized_cad_bom.csv",
        mime="text/csv",
    )
else:
    metrics = calculate_metrics(calculated)
    summary = summarize_materials(calculated)
    metric_cost, metric_units, metric_materials, metric_rows = st.columns(4)
    metric_cost.metric("Estimated cost", f"R$ {metrics.estimated_cost:,.2f}")
    metric_units.metric("Component units", f"{metrics.component_units:,.0f}")
    metric_materials.metric("Materials", metrics.distinct_materials)
    metric_rows.metric("Source rows", metrics.source_rows)

    source_tab, calculated_tab, summary_tab, review_tab = st.tabs(
        ["Source", "Calculated BOM", "Material summary", "Review flags"]
    )
    with source_tab:
        st.dataframe(source, width="stretch")
    with calculated_tab:
        st.dataframe(calculated, width="stretch")
    with summary_tab:
        st.dataframe(summary, width="stretch")
    with review_tab:
        for note in optimization_notes(calculated):
            st.write(f"- {note}")

    csv_output = calculated.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download calculated BOM",
        data=csv_output,
        file_name="calculated_bom.csv",
        mime="text/csv",
    )
