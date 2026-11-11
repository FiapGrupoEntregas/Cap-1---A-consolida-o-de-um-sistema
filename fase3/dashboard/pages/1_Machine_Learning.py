from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml import FEATURES, ideal_profiles, load_dataset, train_models

st.set_page_config(page_title="ML - Cultura Ideal", layout="wide")

st.title("Machine Learning - Recomendação de Cultura")
st.caption(
    "Modelos treinados em `produtos_agricolas.csv` para sugerir a cultura ideal "
    "a partir de parâmetros de solo (N, P, K, pH) e clima (temperatura, umidade, chuva)."
)


@st.cache_data
def get_df() -> pd.DataFrame:
    return load_dataset()


@st.cache_resource(show_spinner="Treinando modelos...")
def get_results():
    return train_models(get_df())


df = get_df()
results = get_results()
metrics = results["metrics"]

tab_eda, tab_perfil, tab_modelos, tab_predict = st.tabs(
    ["EDA", "Perfis Ideais", "Modelos", "Prever"]
)

with tab_eda:
    st.subheader("Visão geral do dataset")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", len(df))
    c2.metric("Atributos", len(FEATURES))
    c3.metric("Culturas", df["label"].nunique())
    c4.metric("Nulos", int(df.isnull().sum().sum()))

    with st.expander("Amostra dos dados"):
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)
        st.dataframe(df.describe().T, use_container_width=True)

    st.markdown("### 1. Distribuição de amostras por cultura")
    counts = df["label"].value_counts().reset_index()
    counts.columns = ["Cultura", "Amostras"]
    fig = px.bar(counts, x="Cultura", y="Amostras", color="Amostras",
                 color_continuous_scale="Greens")
    fig.update_layout(xaxis_tickangle=-45, height=420)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 2. Matriz de correlação entre atributos")
    corr = df[FEATURES].corr()
    fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r",
                    aspect="auto", zmin=-1, zmax=1)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 3. Distribuição de cada atributo (histograma)")
    feat_choice = st.selectbox("Atributo", FEATURES, index=0, key="hist")
    fig = px.histogram(df, x=feat_choice, color="label", nbins=40, marginal="box",
                       opacity=0.75)
    fig.update_layout(height=420, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 4. Boxplot do atributo por cultura")
    box_feat = st.selectbox("Atributo (boxplot)", FEATURES, index=3, key="box")
    fig = px.box(df, x="label", y=box_feat, color="label", points=False)
    fig.update_layout(xaxis_tickangle=-45, showlegend=False, height=460)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 5. Dispersão temperatura x umidade por cultura")
    fig = px.scatter(df, x="temperature", y="humidity", color="label",
                     opacity=0.7, hover_data=FEATURES)
    fig.update_layout(height=480)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 6. Chuva x pH por cultura")
    fig = px.scatter(df, x="rainfall", y="ph", color="label",
                     opacity=0.7, hover_data=FEATURES)
    fig.update_layout(height=480)
    st.plotly_chart(fig, use_container_width=True)

with tab_perfil:
    st.subheader("Perfil ideal de solo e clima")
    culturas_disp = sorted(df["label"].unique())
    default = [c for c in ["rice", "maize", "coffee"] if c in culturas_disp][:3]
    selecionadas = st.multiselect(
        "Selecione até 3 culturas",
        culturas_disp,
        default=default,
        max_selections=3,
    )

    if not selecionadas:
        st.info("Selecione ao menos uma cultura.")
    else:
        perfil = ideal_profiles(df, selecionadas)
        st.dataframe(perfil, use_container_width=True, hide_index=True)

        st.markdown("#### Comparativo visual das médias")
        means = (
            df[df["label"].isin(selecionadas)]
            .groupby("label")[FEATURES]
            .mean()
            .reset_index()
            .melt(id_vars="label", var_name="Atributo", value_name="Média")
        )
        fig = px.bar(means, x="Atributo", y="Média", color="label", barmode="group")
        fig.update_layout(height=460)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Radar (perfil médio normalizado)")
        norm = df[FEATURES].copy()
        norm = (norm - norm.min()) / (norm.max() - norm.min())
        norm["label"] = df["label"]
        rad = norm[norm["label"].isin(selecionadas)].groupby("label").mean().reset_index()
        rad_long = rad.melt(id_vars="label", var_name="Atributo", value_name="Valor")
        fig = px.line_polar(rad_long, r="Valor", theta="Atributo", color="label",
                            line_close=True, range_r=[0, 1])
        fig.update_traces(fill="toself", opacity=0.4)
        st.plotly_chart(fig, use_container_width=True)

with tab_modelos:
    st.subheader("Comparação de desempenho dos modelos")
    st.caption(
        "Split treino/teste 80/20 estratificado + validação cruzada (5 folds). "
        "Métricas em macro-average."
    )

    show = metrics.copy()
    for col in show.columns[1:]:
        show[col] = show[col].astype(float).round(4)
    st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("#### Comparação visual")
    melted = metrics.melt(
        id_vars="Modelo",
        value_vars=["Acurácia", "Precisão (macro)", "Recall (macro)", "F1 (macro)"],
        var_name="Métrica",
        value_name="Valor",
    )
    fig = px.bar(melted, x="Modelo", y="Valor", color="Métrica", barmode="group",
                 range_y=[0.9, 1.0])
    fig.update_layout(height=460, xaxis_tickangle=-20)
    st.plotly_chart(fig, use_container_width=True)

    melhor = metrics.iloc[0]["Modelo"]
    st.success(f"Melhor modelo por F1 (macro): **{melhor}** "
               f"(F1 = {metrics.iloc[0]['F1 (macro)']:.4f})")

    st.markdown("#### Matriz de confusão")
    modelo_cm = st.selectbox("Modelo", metrics["Modelo"].tolist(), key="cm_sel")
    cm, classes = results["confusion"][modelo_cm]
    fig = px.imshow(cm, x=classes, y=classes, text_auto=True,
                    color_continuous_scale="Blues",
                    labels=dict(x="Predito", y="Real", color="Qtd"))
    fig.update_layout(height=640)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Relatório de classificação detalhado"):
        rep = results["reports"][modelo_cm]
        rep_df = pd.DataFrame(rep).T
        st.dataframe(rep_df.round(4), use_container_width=True)

with tab_predict:
    st.subheader("Prever cultura ideal")
    st.caption("Informe os parâmetros e veja a recomendação do modelo escolhido.")

    modelo_nome = st.selectbox("Modelo", list(results["models"].keys()),
                               index=list(results["models"].keys()).index(metrics.iloc[0]["Modelo"]))
    modelo = results["models"][modelo_nome]

    c1, c2, c3, c4 = st.columns(4)
    n = c1.slider("Nitrogênio (N)", 0, 140, 50)
    p = c2.slider("Fósforo (P)", 5, 145, 50)
    k = c3.slider("Potássio (K)", 5, 205, 50)
    ph = c4.slider("pH", 3.5, 10.0, 6.5, 0.1)
    c5, c6, c7 = st.columns(3)
    temp = c5.slider("Temperatura (°C)", 8.0, 44.0, 25.0, 0.1)
    hum = c6.slider("Umidade (%)", 14.0, 100.0, 70.0, 0.5)
    rain = c7.slider("Chuva (mm)", 20.0, 300.0, 100.0, 1.0)

    sample = pd.DataFrame([[n, p, k, temp, hum, ph, rain]], columns=FEATURES)
    pred = modelo.predict(sample)[0]

    st.markdown(f"### Cultura recomendada: **`{pred}`**")

    if hasattr(modelo.named_steps["clf"], "predict_proba"):
        proba = modelo.predict_proba(sample)[0]
        classes = modelo.named_steps["clf"].classes_
        top = (
            pd.DataFrame({"Cultura": classes, "Probabilidade": proba})
            .sort_values("Probabilidade", ascending=False)
            .head(5)
        )
        fig = px.bar(top, x="Probabilidade", y="Cultura", orientation="h",
                     color="Probabilidade", color_continuous_scale="Greens")
        fig.update_layout(height=320, yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig, use_container_width=True)
