from __future__ import annotations

import pandas as pd
import streamlit as st

from bom_engine import (
    calculate_bom,
    calculate_metrics,
    optimization_notes,
    summarize_materials,
)


st.set_page_config(page_title="Engineering BOM Intelligence", layout="wide")

st.title("Engineering BOM Intelligence")
st.caption("Deterministic material, consumption and estimated-cost analysis for engineering BOMs")


def load_source(uploaded_file: object | None) -> pd.DataFrame:
    if uploaded_file is None:
        raise ValueError("Upload a CSV or XLSX file to begin the analysis")
    name = str(getattr(uploaded_file, "name", "")).lower()
    if name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file)
    return pd.read_csv(uploaded_file)


st.info(
    "This application uses deterministic formulas. The review notes are rule-based and the "
    "estimated costs are not production quotations."
)

uploaded = st.file_uploader("Upload a CSV or XLSX BOM", type=["csv", "xlsx"])

if uploaded is None:
    st.markdown(
        "The expected schema is documented in the repository README. "
        "No engineering dimensions or cost tables are bundled with this public prototype."
    )
    st.stop()

try:
    source = load_source(uploaded)
    calculated = calculate_bom(source)
except (ValueError, OSError, pd.errors.ParserError) as error:
    st.error(f"Input validation failed: {error}")
    st.stop()

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
    st.dataframe(source, use_container_width=True)

with calculated_tab:
    st.dataframe(calculated, use_container_width=True)

with summary_tab:
    st.dataframe(summary, use_container_width=True)

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
