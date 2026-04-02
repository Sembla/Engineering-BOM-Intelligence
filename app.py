import io
import math
from typing import Optional

import pandas as pd
import streamlit as st

st.set_page_config(page_title='Engineering BOM Intelligence', layout='wide')

st.title('🏗️ Engineering BOM Intelligence')
st.caption('Generate BOM, estimate cost, and spot simple optimization opportunities.')

DEFAULT_CSV = """item,familia,tipo,largura_mm,altura_mm,profundidade_mm,quantidade,material,custo_unitario_m2,perda_percentual
BASE,GONDOLA,PAINEL,1000,2200,18,2,MDP BRANCO TX,95,3
PRATELEIRA,GONDOLA,PRATELEIRA,900,300,18,8,MDP BRANCO TX,95,3
LATERAL,GONDOLA,LATERAL,400,2200,18,2,MDP BRANCO TX,95,3
RODAPE,GONDOLA,RODAPE,1000,100,18,1,MDP BRANCO TX,95,3
PORTA ETIQUETA,ACESSORIO,PERFIL,900,35,1,8,PVC,18,0
"""


def load_dataframe(uploaded_file: Optional[io.BytesIO]) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.read_csv(io.StringIO(DEFAULT_CSV))
    if uploaded_file.name.lower().endswith('.xlsx'):
        return pd.read_excel(uploaded_file)
    return pd.read_csv(uploaded_file)


def calculate_bom(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    numeric_cols = [
        'largura_mm', 'altura_mm', 'profundidade_mm', 'quantidade',
        'custo_unitario_m2', 'perda_percentual'
    ]
    for col in numeric_cols:
        work[col] = pd.to_numeric(work[col], errors='coerce').fillna(0)

    work['area_m2_unit'] = (work['largura_mm'] * work['altura_mm']) / 1_000_000
    work['area_m2_total'] = work['area_m2_unit'] * work['quantidade']
    work['area_m2_com_perda'] = work['area_m2_total'] * (1 + work['perda_percentual'] / 100)
    work['custo_total_estimado'] = work['area_m2_com_perda'] * work['custo_unitario_m2']
    work['volume_m3_total'] = (
        work['largura_mm'] * work['altura_mm'] * work['profundidade_mm'] * work['quantidade']
    ) / 1_000_000_000
    return work


def material_summary(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby('material', dropna=False)[['quantidade', 'area_m2_com_perda', 'custo_total_estimado']]
        .sum()
        .reset_index()
        .sort_values('custo_total_estimado', ascending=False)
    )
    return grouped


def optimization_notes(df: pd.DataFrame) -> list[str]:
    notes = []
    waste_items = df[df['perda_percentual'] > 5]
    if not waste_items.empty:
        notes.append(
            f"{len(waste_items)} item(ns) com perda acima de 5%. Vale revisar plano de corte e padronização dimensional."
        )

    expensive = df.sort_values('custo_total_estimado', ascending=False).head(3)
    if not expensive.empty:
        top_names = ', '.join(expensive['item'].astype(str).tolist())
        notes.append(f"Itens de maior impacto no custo: {top_names}.")

    thin_parts = df[df['profundidade_mm'] < 10]
    if not thin_parts.empty:
        notes.append(
            'Há componentes muito finos. Confira se eles devem entrar como área, comprimento ou acessório unitário.'
        )

    repeated_materials = df['material'].nunique()
    if repeated_materials > 4:
        notes.append(
            'Muitos materiais diferentes no projeto. Menos variação costuma simplificar compras e produção.'
        )

    if not notes:
        notes.append('Estrutura está enxuta. Próximo passo: integrar tabela de preços reais e regras por família de produto.')
    return notes


uploaded = st.file_uploader('Upload CSV ou XLSX de projeto', type=['csv', 'xlsx'])
source_df = load_dataframe(uploaded)

st.subheader('1) Dados de entrada')
st.dataframe(source_df, use_container_width=True)

bom_df = calculate_bom(source_df)
summary_df = material_summary(bom_df)
notes = optimization_notes(bom_df)

st.subheader('2) BOM calculada')
st.dataframe(bom_df, use_container_width=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric('Custo total estimado', f"R$ {bom_df['custo_total_estimado'].sum():,.2f}")
with col2:
    st.metric('Área total c/ perda', f"{bom_df['area_m2_com_perda'].sum():,.2f} m²")
with col3:
    st.metric('Itens totais', f"{int(bom_df['quantidade'].sum())}")

st.subheader('3) Resumo por material')
st.dataframe(summary_df, use_container_width=True)

st.subheader('4) Insights de otimização')
for note in notes:
    st.write(f'- {note}')

csv_output = bom_df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    'Baixar BOM calculada (CSV)',
    data=csv_output,
    file_name='bom_calculada.csv',
    mime='text/csv'
)
