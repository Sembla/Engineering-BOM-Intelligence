# 🏗️ Engineering BOM Intelligence

AI-inspired engineering BOM assistant built with Python and Streamlit.

## Overview
This project reads engineering component data, calculates bill of materials metrics, estimates total cost, and highlights simple optimization opportunities.

## Features
- CSV/XLSX upload
- BOM calculation
- Estimated area and cost
- Material summary
- Optimization notes
- CSV export

## Tech Stack
- Python
- Pandas
- Streamlit
- OpenPyXL

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Sample input columns
- item
- familia
- tipo
- largura_mm
- altura_mm
- profundidade_mm
- quantidade
- material
- custo_unitario_m2
- perda_percentual

## Business value
This can support product engineering, furniture development, quoting workflows, and BOM standardization.

## Author
Henrique Sembla
