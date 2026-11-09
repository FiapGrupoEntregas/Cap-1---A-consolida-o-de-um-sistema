import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

from core.ml_pipeline import TRAINABLE_TARGETS, predict_next, train_regression

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Dashboard de Solo - IA", layout="wide")

st.title("Dashboard de Análise de Solo com Machine Learning")
st.markdown(
    "Este painel busca os dados mensais da API e treina um modelo de regressão "
    "para prever uma variável do solo com base nos sensores."
)

st.sidebar.header("Filtros de busca")
year = st.sidebar.number_input("Ano", min_value=2000, max_value=2100, value=datetime.now().year)
month = st.sidebar.number_input("Mês", min_value=1, max_value=12, value=datetime.now().month)
target = st.sidebar.selectbox(
    "Variável que deseja prever",
    TRAINABLE_TARGETS,
    format_func=lambda x: {
        "soil_moisture_percent": "Umidade do solo (%)",
        "ph": "pH",
        "nitrogen": "Nitrogênio",
        "phosphorus": "Fósforo",
        "potassium": "Potássio",
        "air_temperature": "Temperatura do ar (°C)",
        "air_humidity": "Umidade do ar (%)",
        "light_percent": "Luminosidade (%)",
    }.get(x, x),
)
model_type = "random_forest"

if st.sidebar.button("Buscar e treinar modelo", type="primary"):
    with st.spinner("Carregando dados da API..."):
        try:
            response = requests.get(
                f"{API_URL}/soil/month/{int(year)}/{int(month)}",
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            st.error(f"Erro ao buscar dados da API: {exc}")
            st.stop()

    if not data:
        st.warning("Nenhum dado encontrado para o mês selecionado.")
        st.stop()

    df = pd.DataFrame(data)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    with st.spinner("Treinando modelo..."):
        try:
            result = train_regression(df, target=target, model_type=model_type)
        except Exception as exc:
            st.error(f"Erro durante o treinamento: {exc}")
            st.stop()

    st.success("Treinamento concluído!")

    st.subheader("Métricas do modelo")
    metrics = result["metrics"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("R²", f"{metrics['r2']:.4f}")
    col2.metric("MAE", f"{metrics['mae']:.4f}")
    col3.metric("MSE", f"{metrics['mse']:.4f}")
    col4.metric("RMSE", f"{metrics['rmse']:.4f}")

    with st.expander("Como interpretar essas métricas?"):
        st.markdown(
            """
            - **R² (Coeficiente de Determinação):** varia de menos infinito até 1.
              Quanto mais próximo de 1, melhor o modelo consegue explicar os dados.
              Um valor próximo de 0 indica que o modelo não é melhor do que usar a média.

            - **MAE (Erro Absoluto Médio):** média dos erros em valores absolutos.
              Mostra, em média, quanto a previsão erra para mais ou para menos.
              Quanto menor, melhor.

            - **MSE (Erro Quadrático Médio):** média dos erros elevados ao quadrado.
              Penaliza mais os erros grandes, então valores altos indicam previsões bem distantes do real.

            - **RMSE (Raiz do Erro Quadrático Médio):** é a raiz quadrada do MSE,
              trazendo a unidade de volta para a mesma da variável prevista.
              Facilita entender o erro médio na escala real do dado.
            """
        )

    st.subheader("Gráfico: Real vs Previsto")
    chart_df = pd.DataFrame({
        "Índice": range(len(result["y_test"])),
        "Valor real": result["y_test"],
        "Valor previsto": result["y_pred"],
    })
    st.line_chart(chart_df.set_index("Índice"), use_container_width=True)

    st.subheader("Comparação entre primeiros valores")
    comparison_df = pd.DataFrame({
        "Real": result["y_test"][:20],
        "Previsto": result["y_pred"][:20],
    })
    st.bar_chart(comparison_df, use_container_width=True)

    st.subheader("Previsão para o próximo registro")
    last_row = df.sort_values("created_at").iloc[-1]
    next_prediction = predict_next(
        result["model"],
        result["scaler"],
        last_row,
        list(df.columns),
        target,
    )
    if next_prediction is not None:
        st.metric(
            label=f"Previsão de '{target}' para o próximo ciclo",
            value=f"{next_prediction:.2f}",
        )
    else:
        st.info("Não foi possível gerar a previsão com as colunas disponíveis.")

    st.subheader("Dados recebidos")
    st.write(f"Total de registros: **{len(df)}**")
    st.dataframe(df.head(20), use_container_width=True)

else:
    st.info("Selecione os filtros no menu lateral e clique em 'Buscar e treinar modelo'.")
