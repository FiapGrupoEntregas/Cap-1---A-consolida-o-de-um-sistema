"""Dashboard central da FarmTech Solutions (Fase 7): a dashboard da Fase 4 evoluída.

Páginas:
- Início: visão do sistema e estado dos serviços;
- Análise de solo (Fase 4): a dashboard original, sem mudanças de comportamento;
- Central de serviços: um botão para cada serviço das Fases 1, 2, 3 e 6 (e o alerta da AWS).

Os botões chamam o `main.py` da raiz (ver core/servicos.py), que é o mesmo caminho usado no terminal.

    cd fase4/src && uv run streamlit run app.py        # ou: python3 main.py fase4-dashboard
"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # .env único da raiz

st.set_page_config(page_title="FarmTech Solutions — Dashboard central", page_icon="🌱", layout="wide")

pagina = st.navigation([
    st.Page("paginas/inicio.py", title="Início", icon="🏠", default=True),
    st.Page("paginas/analise_solo.py", title="Análise de solo (Fase 4)", icon="📈"),
    st.Page("paginas/central.py", title="Central de serviços", icon="🎛️"),
])
pagina.run()
