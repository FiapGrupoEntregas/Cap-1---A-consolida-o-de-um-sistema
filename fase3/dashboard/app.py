import os
from pathlib import Path

import oracledb
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="FarmTech Dashboard",
    layout="wide",
)

ROOT = Path(__file__).resolve().parent.parent


@st.cache_data(ttl=60)
def load_from_oracle() -> pd.DataFrame:
    user = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_PASSWORD")
    dsn = os.getenv("ORACLE_DSN")
    if not all([user, password, dsn]):
        raise RuntimeError("Credenciais Oracle não definidas no .env")
    with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
        return pd.read_sql("SELECT * FROM SENSOR_DADOS ORDER BY ID", conn)


def load_data() -> pd.DataFrame:
    return load_from_oracle()


st.sidebar.title("FarmTech")
st.sidebar.caption("Dashboard de Sensores - Fase 3")

try:
    df = load_data()
    st.sidebar.success(f"{len(df)} registros carregados")
except Exception as e:
    st.sidebar.error(f"Falha Oracle: {e}")
    st.stop()

if df.empty:
    st.warning("Nenhum dado disponível.")
    st.stop()

st.sidebar.subheader("Filtros")
ph_min, ph_max = st.sidebar.slider(
    "Faixa de pH", 0.0, 14.0, (float(df["PH"].min()), float(df["PH"].max())), 0.1
)
umid_min, umid_max = st.sidebar.slider(
    "Faixa de Umidade (%)",
    0.0,
    100.0,
    (float(df["UMIDADE"].min()), float(df["UMIDADE"].max())),
    0.5,
)
irrig_filter = st.sidebar.multiselect(
    "Status Irrigação", df["IRRIGACAO"].unique().tolist(), default=df["IRRIGACAO"].unique().tolist()
)

mask = (
    df["PH"].between(ph_min, ph_max)
    & df["UMIDADE"].between(umid_min, umid_max)
    & df["IRRIGACAO"].isin(irrig_filter)
)
fdf = df[mask].copy()

st.title("FarmTech Solutions – Dashboard de Sensores")
st.caption("Monitoramento de umidade, pH, nutrientes (NPK) e status de irrigação")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Registros", len(fdf))
c2.metric("Umidade média", f"{fdf['UMIDADE'].mean():.1f}%")
c3.metric("pH médio", f"{fdf['PH'].mean():.2f}")
on_count = (fdf["IRRIGACAO"] == "ON").sum()
c4.metric("Irrigação ON", int(on_count))
c5.metric("Irrigação OFF", int((fdf["IRRIGACAO"] == "OFF").sum()))

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Umidade por registro")
    fig = px.bar(
        fdf,
        x="ID",
        y="UMIDADE",
        color="IRRIGACAO",
        color_discrete_map={"ON": "#2ecc71", "OFF": "#e74c3c"},
        labels={"UMIDADE": "Umidade (%)", "ID": "ID do Sensor"},
    )
    fig.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="Limite 60%")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("pH por registro")
    fig = px.line(
        fdf,
        x="ID",
        y="PH",
        markers=True,
        labels={"PH": "pH", "ID": "ID do Sensor"},
    )
    fig.add_hrect(y0=6.0, y1=7.0, fillcolor="green", opacity=0.15, annotation_text="Faixa ideal")
    st.plotly_chart(fig, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    st.subheader("Status de Irrigação")
    pie_df = fdf["IRRIGACAO"].value_counts().reset_index()
    pie_df.columns = ["Status", "Quantidade"]
    fig = px.pie(
        pie_df,
        names="Status",
        values="Quantidade",
        color="Status",
        color_discrete_map={"ON": "#2ecc71", "OFF": "#e74c3c"},
        hole=0.4,
    )
    st.plotly_chart(fig, use_container_width=True)

with col4:
    st.subheader("Presença de Nutrientes (NPK)")
    nutri = pd.DataFrame(
        {
            "Nutriente": ["Nitrogênio (N)", "Fósforo (P)", "Potássio (K)"],
            "Presente": [
                (fdf["NITROGENIO"] == "S").sum(),
                (fdf["FOSFORO"] == "S").sum(),
                (fdf["POTASSIO"] == "S").sum(),
            ],
            "Ausente": [
                (fdf["NITROGENIO"] == "N").sum(),
                (fdf["FOSFORO"] == "N").sum(),
                (fdf["POTASSIO"] == "N").sum(),
            ],
        }
    )
    fig = px.bar(
        nutri.melt(id_vars="Nutriente", var_name="Status", value_name="Qtd"),
        x="Nutriente",
        y="Qtd",
        color="Status",
        barmode="group",
        color_discrete_map={"Presente": "#27ae60", "Ausente": "#c0392b"},
    )
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Dispersão Umidade x pH")
fig = px.scatter(
    fdf,
    x="UMIDADE",
    y="PH",
    color="IRRIGACAO",
    size=[10] * len(fdf),
    hover_data=["ID", "NITROGENIO", "FOSFORO", "POTASSIO"],
    color_discrete_map={"ON": "#2ecc71", "OFF": "#e74c3c"},
    labels={"UMIDADE": "Umidade (%)", "PH": "pH"},
)
fig.add_hrect(y0=6.0, y1=7.0, fillcolor="green", opacity=0.10)
fig.add_vline(x=60, line_dash="dash", line_color="orange")
st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("Dados detalhados")
st.dataframe(
    fdf,
    use_container_width=True,
    hide_index=True,
    column_config={
        "UMIDADE": st.column_config.ProgressColumn(
            "Umidade (%)", min_value=0, max_value=100, format="%.1f"
        ),
        "PH": st.column_config.NumberColumn("pH", format="%.1f"),
    },
)

st.download_button(
    "Baixar CSV filtrado",
    fdf.to_csv(index=False).encode("utf-8"),
    file_name="sensor_dados_filtrado.csv",
    mime="text/csv",
)
