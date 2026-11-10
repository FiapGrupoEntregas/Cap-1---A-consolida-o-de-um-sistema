"""Central de serviços: um bloco por fase, com botões que chamam o main.py da raiz."""

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import servicos as sv

st.title("Central de serviços")
st.caption("Cada botão roda `python3 main.py <serviço>` na raiz do repositório e mostra o resultado aqui.")


def saida_texto(r: sv.Resultado, titulo: str) -> None:
    """Mostra a saída de um serviço de terminal (ou o erro)."""
    if r.ok:
        st.success(titulo)
        st.code(r.stdout.strip() or "(sem saída)")
    else:
        sv.mostrar_erro(r)


def bloco_servidor(servico: str, rotulo: str, url: str, dica: str) -> None:
    """Botões iniciar/parar de um serviço que fica no ar (API, dashboard da Fase 3)."""
    ativo = sv.no_ar(servico) or sv.porta_aberta("127.0.0.1", sv.PORTAS[servico])
    c1, c2, c3 = st.columns([2, 1, 1])
    c1.markdown(f"**{rotulo}** — {'🟢 no ar' if ativo else '⚪ parado'} · [{url}]({url})")
    if c2.button("Iniciar", key=f"ini-{servico}", disabled=ativo, width="stretch"):
        sv.iniciar(servico)
        st.toast(f"{rotulo}: iniciando...")
        st.rerun()
    if c3.button("Parar", key=f"par-{servico}", disabled=not sv.no_ar(servico), width="stretch"):
        sv.parar(servico)
        st.rerun()
    if ativo and not sv.no_ar(servico):
        st.caption(f"A porta {sv.PORTAS[servico]} já está em uso por um processo fora desta dashboard.")
    st.caption(dica)
    if log := sv.log_de(servico, 8):
        with st.expander("Últimas linhas do log"):
            st.code(log)


# ----------------------------------------------------------------------------- Fase 1
st.header("Fase 1 — Área de plantio e insumos", divider="green")
with st.form("fase1"):
    cultura = st.radio("Cultura", ["manga", "cana"], horizontal=True,
                       captions=["terreno retangular, insumo em litros", "pivô circular, fertilizante em kg"])
    c1, c2, c3, c4 = st.columns(4)
    largura = c1.number_input("Largura (m)", min_value=0.0, value=100.0)
    comprimento = c2.number_input("Comprimento (m)", min_value=0.0, value=200.0)
    ruas = c3.number_input("Ruas", min_value=1, value=10)
    litros = c4.number_input("Litros por metro (L/m)", min_value=0.0, value=0.5)
    c5, c6 = st.columns(2)
    raio = c5.number_input("Raio do pivô (m)", min_value=0.0, value=50.0)
    kg_m2 = c6.number_input("Fertilizante (kg/m²)", min_value=0.0, value=0.2)
    salvar = st.checkbox("Gravar o resultado no CSV da Fase 1")
    calcular = st.form_submit_button("Calcular", type="primary")

if calcular:
    args = (["--cultura", "manga", "--largura", largura, "--comprimento", comprimento, "--ruas", int(ruas), "--litros-por-metro", litros]
            if cultura == "manga" else ["--cultura", "cana", "--raio", raio, "--kg-por-m2", kg_m2])
    if salvar:
        args.append("--salvar")
    with st.spinner("Calculando..."):
        r = sv.rodar("fase1-calculo", *args)
    if r.ok:
        res = r.json()
        m1, m2 = st.columns(2)
        m1.metric(f"Área ({res['tipo_area'].lower()})", f"{res['area_m2']:,.2f} m²")
        m2.metric("Insumo", f"{res['insumo']:,.2f} {res['unidade_insumo']}")
        if "id_csv" in res:
            st.success(f"Registro gravado no CSV com id {res['id_csv']}.")
        with st.expander("JSON devolvido"):
            st.json(res)
    else:
        sv.mostrar_erro(r)

c1, c2 = st.columns(2)
if c1.button("Estatística dos registros (R)", width="stretch"):
    with st.spinner("Rodando Rscript..."):
        saida_texto(sv.rodar("fase1-estatistica", timeout=600), "Estatística em R")
if c2.button("Previsão do tempo (R)", width="stretch"):
    with st.spinner("Rodando Rscript..."):
        saida_texto(sv.rodar("fase1-clima", timeout=600), "Previsão do tempo em R")

# ----------------------------------------------------------------------------- Fase 2
st.header("Fase 2 — Irrigação automática (ESP32)", divider="green")
col_a, col_b = st.columns([3, 2])
with col_a:
    if st.button("Previsão do tempo → código S/L/C para o ESP32", type="primary", width="stretch"):
        with st.spinner("Consultando a Open-Meteo..."):
            r = sv.rodar("fase2-clima", timeout=60)
        if r.ok:
            codigo = next((l.split("[")[1].split("]")[0].strip() for l in r.stdout.splitlines() if "Código para ESP32" in l), "?")
            nomes = {"S": "Seco → irrigação normal", "L": "Chuva leve → irrigação reduzida", "C": "Chuva forte → suspender irrigação"}
            st.metric("Código para o Monitor Serial do Wokwi", codigo, nomes.get(codigo, ""))
            with st.expander("Saída completa"):
                st.code(r.stdout.strip())
        else:
            sv.mostrar_erro(r)
    if st.button("Regressão logística da decisão de irrigar (R)", width="stretch"):
        with st.spinner("Rodando Rscript..."):
            saida_texto(sv.rodar("fase2-regressao", timeout=600), "Regressão em R")
    st.caption("O ESP32 roda no Wokwi (abrir `fase2/` no VS Code). Cole o código S/L/C no Monitor Serial.")
with col_b:
    circuito = sv.IMAGENS / "fase2-circuito-wokwi.png"
    if circuito.exists():
        st.image(str(circuito), caption="Circuito da Fase 2 no Wokwi", width="stretch")

# ----------------------------------------------------------------------------- Fase 3
st.header("Fase 3 — Banco de dados Oracle", divider="green")
if st.button("Consultar o Oracle (consulta.sql)", type="primary", width="stretch"):
    with st.spinner("Executando as consultas..."):
        r = sv.rodar("fase3-consultas", "--json", timeout=120)
    if r.ok:
        for i, c in enumerate(r.json(), 1):
            st.markdown(f"**Consulta {i}:** `{' '.join(c['sql'].split())}`")
            st.dataframe(pd.DataFrame(c["linhas"], columns=c["colunas"]), width="stretch", hide_index=True)
    else:
        sv.mostrar_erro(r, "Não foi possível consultar o Oracle")
bloco_servidor("fase3-dashboard", "Dashboard da Fase 3 (Streamlit)", sv.URL_DASH_FASE3,
               "Dashboard original da Fase 3, com a página de ML de recomendação de cultura.")

# ----------------------------------------------------------------------------- Fase 4
st.header("Fase 4 — API dos sensores de solo", divider="green")
bloco_servidor("fase4-api", "API FastAPI", f"{sv.API_URL}/docs",
               "A página **Análise de solo** e o ESP32 da Fase 4 dependem desta API.")

# ----------------------------------------------------------------------------- Fase 6
st.header("Fase 6 — Detecção de trator e vaca (YOLOv5)", divider="green")
amostras = sorted((sv.RAIZ / "fase6" / "data" / "amostras").glob("*.jpg"))
c1, c2 = st.columns([3, 1])
arquivo = c1.file_uploader("Envie uma foto (jpg/png)", type=["jpg", "jpeg", "png"])
amostra = c2.selectbox("...ou use uma amostra", ["(nenhuma)", *[a.name for a in amostras]])
conf = st.slider("Confiança mínima", 0.05, 0.95, 0.25, 0.05)
if st.button("Detectar", type="primary", width="stretch"):
    if arquivo is not None:
        destino = Path(tempfile.mkdtemp(prefix="farmtech-")) / arquivo.name
        destino.write_bytes(arquivo.getvalue())
        caminho = destino
    elif amostra != "(nenhuma)":
        caminho = sv.RAIZ / "fase6" / "data" / "amostras" / amostra
    else:
        caminho = None
        st.warning("Envie uma foto ou escolha uma amostra.")
    if caminho:
        with st.spinner("Detectando (na 1ª vez o YOLOv5 é baixado e pode demorar)..."):
            r = sv.rodar("fase6", str(caminho), "--conf", conf, timeout=900)
        if r.ok:
            res = r.json()
            c1, c2 = st.columns([3, 2])
            c1.image(res["imagem_anotada"], caption=Path(res["imagem"]).name, width="stretch")
            with c2:
                m1, m2 = st.columns(2)
                m1.metric("Tratores", res["resumo"].get("trator", 0))
                m2.metric("Vacas", res["resumo"].get("vaca", 0))
                if res["deteccoes"]:
                    st.dataframe(pd.DataFrame([{"classe": d["classe"], "confiança": d["confianca"], **d["caixa"]} for d in res["deteccoes"]]),
                                 width="stretch", hide_index=True)
                else:
                    st.info("Nenhum trator ou vaca acima da confiança escolhida.")
                for acao in res["acoes_sugeridas"]:
                    st.warning(f"Ação sugerida: {acao}")
        else:
            sv.mostrar_erro(r, "A detecção falhou")

# ----------------------------------------------------------------------------- Alerta
st.header("Alerta na AWS — Fase 7", divider="orange")
st.markdown(
    "Avalia as leituras dos sensores (`SOIL_DATA`, Fase 4) com as regras de umidade, pH e N/P/K e publica "
    "o alerta com a **ação corretiva** no tópico do Amazon SNS, que envia o e-mail aos funcionários. "
    f"Destino atual: **{'floci (AWS local)' if sv.os.getenv('AWS_ENDPOINT_URL') else 'Amazon SNS'}**."
)
c1, c2, c3 = st.columns([2, 2, 1])
fonte_alerta = c1.selectbox("Leituras", ["últimas leituras do Oracle", "simular: seco", "simular: acido", "simular: alcalino",
                                         "simular: npk", "simular: tudo", "simular: ok"])
ultimas = c2.number_input("Quantas leituras recentes", min_value=1, max_value=50, value=1,
                          disabled=fonte_alerta != "últimas leituras do Oracle")
forcar = c3.checkbox("Forçar reenvio", help="Publica mesmo que a mesma condição tenha sido alertada há menos de 60 min")
if st.button("Verificar sensores e alertar", type="primary", width="stretch"):
    args = ["--ultimas", int(ultimas)] if fonte_alerta.startswith("últimas") else ["--simular", fonte_alerta.split(": ")[1]]
    if forcar:
        args.append("--forcar")
    with st.spinner("Avaliando as leituras e publicando..."):
        r = sv.rodar("alerta", *args, timeout=180)
    if r.codigo in (0, 4):
        res = r.json()
        if not res["alertas"]:
            st.success("Nenhuma regra disparou: leituras dentro dos limites.")
        else:
            st.dataframe(pd.DataFrame(res["alertas"])[["problema", "acao", "valor"]], width="stretch", hide_index=True)
            if res["publicado"]:
                st.success(f"Alerta publicado em {res['destino']} (MessageId {res.get('message_id')}).")
            elif res.get("erro"):
                st.error(f"Não foi possível publicar: {res['erro']}")
            elif res["repetidos_nao_enviados"]:
                st.info("Nada publicado: essas condições já foram alertadas há menos de 60 min. Marque \"Forçar reenvio\" para repetir.")
            if "mensagem" in res:
                with st.expander("E-mail que foi (ou seria) enviado"):
                    st.markdown(f"**Assunto:** {res['mensagem']['assunto']}")
                    st.code(res["mensagem"]["corpo"])
        with st.expander("Leituras avaliadas (JSON)"):
            st.json(res["avaliacoes"])
    else:
        sv.mostrar_erro(r, "O serviço de alerta falhou")
