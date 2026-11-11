"""Página inicial: o que é o sistema e o estado de cada serviço."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import servicos as sv

st.title("FarmTech Solutions — Dashboard central")
st.markdown(
    "As entregas das Fases 1 a 6 reunidas num sistema só. A **Análise de solo** é a dashboard "
    "original da Fase 4; a **Central de serviços** dispara cada fase por um botão, pelo mesmo "
    "`main.py` que funciona no terminal."
)

st.subheader("Estado dos serviços")
col1, col2, col3, col4 = st.columns(4)
with st.spinner("Conferindo..."):
    env_ok = sv.env_configurado()
    api_ok = sv.api_responde()
    ora_ok = sv.oracle_acessivel()
    aws_ok = sv.aws_configurada()

col1.metric("Arquivo .env", "configurado" if env_ok else "faltando")
col2.metric(f"API da Fase 4 (:{sv.porta_da_api()})", "no ar" if api_ok else "parada")
col3.metric("Oracle da FIAP", "acessível" if ora_ok else "sem acesso")
col4.metric("Alerta AWS", "configurado" if aws_ok else "em construção")

if not env_ok:
    st.warning("Copie `.env.example` para `.env` na raiz e preencha `ORACLE_USER` e `ORACLE_PASSWORD`.")
if not api_ok:
    st.info("A API da Fase 4 pode ser iniciada na página **Central de serviços** (bloco Fase 4).")

st.subheader("As fases dentro do sistema")
st.markdown(
    """
| Fase | O que entra no sistema | Como disparar |
|---|---|---|
| 1 — Base de dados inicial | Cálculo de área e insumos (manga e cana) e estatística em R | Central → Fase 1 ou `main.py fase1-calculo` |
| 2 — IoT e automação | Previsão de chuva para o ESP32 de irrigação e regressão em R | Central → Fase 2 ou `main.py fase2-clima` |
| 3 — Banco de dados | Consultas no Oracle (`SENSOR_DADOS`) e dashboard própria | Central → Fase 3 ou `main.py fase3-consultas` |
| 4 — Data Science | API + análise de solo com Random Forest (`SOIL_DATA`) | Página **Análise de solo** |
| 6 — Visão computacional | Detecção de trator e vaca com o YOLOv5 treinado | Central → Fase 6 ou `main.py fase6 <imagem>` |
| 7 — Alerta na AWS | Regras sobre as leituras → e-mail pelo Amazon SNS | Central → Alerta (em construção) |
"""
)
st.caption("Documentação completa no README da raiz e em docs/.")
