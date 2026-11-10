# Como usar o repositório e o que foi alterado

Guia rápido para quem vai trabalhar na entrega da Fase 7 (FarmTech Solutions). O
[`README.md`](README.md) é a documentação integrada para quem avalia; este arquivo é o
registro do que mudou em cada etapa e de como usar o que foi feito. O que ainda falta está em
[`docs/plano-entrega/`](docs/plano-entrega/README.md).

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/): cada fase tem o próprio `pyproject.toml` e `uv.lock`; o uv
  baixa a versão certa de Python.
- `git` e internet: a Fase 6 clona o YOLOv5 na primeira execução; as Fases 3 e 4 usam o Oracle da FIAP.
- R 4.2+ (Fases 1 e 2), VS Code com PlatformIO e Wokwi (ESP32 das Fases 2 e 4), Docker (floci).

## Passo a passo

### 1. Clonar e configurar o `.env`

```bash
git clone https://github.com/FiapGrupoEntregas/Cap-1---A-consolida-o-de-um-sistema.git
cd Cap-1---A-consolida-o-de-um-sistema
git checkout feature/entrega-cap-1-fase7
cp .env.example .env        # preencher ORACLE_USER e ORACLE_PASSWORD (RM e senha da FIAP)
```

Um único `.env` na raiz vale para todas as fases: cada script chama `load_dotenv()`, que sobe as
pastas até encontrá-lo. Não crie `.env` dentro das pastas das fases.

### 2. Disparar qualquer serviço: `python3 main.py` (frente 02, concluída)

```bash
python3 main.py listar                                    # lista os serviços
python3 main.py fase1-calculo --cultura manga --largura 100 --comprimento 200 --ruas 10 --litros-por-metro 0.5
python3 main.py fase2-clima
python3 main.py fase3-consultas                           # precisa do .env
python3 main.py fase4-api                                 # porta 8000; Ctrl+C para parar
python3 main.py fase6 fase6/data/amostras/vaca_02.jpg --conf 0.4
```

- Só a biblioteca padrão do Python: roda com qualquer `python3`. Cada serviço executa no ambiente
  da própria fase, com `uv run --project`, a partir da pasta da fase.
- Argumentos depois do nome vão para o serviço (com ou sem `--`). Caminhos relativos são
  convertidos para absolutos antes, porque o serviço roda em outra pasta.
- Se faltar `uv`, R ou o `.env`, o `main.py` explica o que fazer e sai com código 1. Serviço
  inexistente sai com 2; `alerta` ainda não existe e sai com 3.
- Portas: API na 8000, Streamlit da Fase 3 na 8502, dashboard da Fase 4 na 8501. Se alguma estiver
  ocupada, passe outra: `python3 main.py fase4-api --port 8001`.

### 2a. Rodar a detecção da Fase 6 diretamente (frente 01, concluída)

```bash
cd fase6
uv sync                                                 # 1ª vez: ~1,5 GB (PyTorch para CPU + YOLOv5)
uv run python src/detect.py data/amostras/vaca_02.jpg   # imprime o JSON; imagem anotada em saidas/
uv run python src/detect.py minha_foto.jpg --conf 0.4 --saida /tmp/deteccoes
```

Exemplo de saída:

```json
{
  "imagem": "data/amostras/vaca_02.jpg",
  "imagem_anotada": ".../fase6/saidas/vaca_02_20261108-232835.jpg",
  "limite_confianca": 0.25,
  "deteccoes": [{"classe": "vaca", "confianca": 0.836, "caixa": {"x1": 180, "y1": 111, "x2": 820, "y2": 469}}],
  "resumo": {"trator": 0, "vaca": 1},
  "acoes_sugeridas": ["animal na área monitorada: verificar cercas e afastar o rebanho da lavoura"]
}
```

- Só o JSON vai para o stdout; os logs do YOLOv5 vão para o stderr. Assim o `main.py` da raiz e a
  dashboard (frentes 02 e 03) podem ler o resultado com `json.loads`.
- Código de saída `0` quando há detecções e `2` quando não há.
- Para abrir o notebook de treino: `uv sync --group notebook && uv run jupyter lab`.

### 3. Abrir a dashboard central e disparar as fases por botão (frente 03, concluída)

```bash
python3 main.py fase4-dashboard            # abre http://localhost:8501
# ou, sem o main.py:
cd fase4/src && uv run streamlit run app.py
# se a 8501 estiver ocupada:
python3 main.py fase4-dashboard --server.port 8503
```

Na primeira vez o `uv` cria o ambiente da Fase 4 (FastAPI, Streamlit, scikit-learn). A dashboard
tem três páginas, no menu da esquerda:

1. **Início:** estado do `.env`, da API da Fase 4, do Oracle e do alerta AWS, mais o mapa das fases.
2. **Análise de solo (Fase 4):** a dashboard original. Precisa da API no ar: inicie-a no bloco
   "Fase 4" da Central (ou `python3 main.py fase4-api` noutro terminal), escolha ano e mês e clique
   em "Buscar e treinar modelo".
3. **Central de serviços**, um bloco por fase:
   - **Fase 1:** escolha manga ou cana, preencha as medidas e clique em **Calcular**; marque "Gravar
     no CSV" para salvar como o programa original. Botões **Estatística (R)** e **Previsão do tempo (R)**
     rodam os scripts R (precisa do R instalado).
   - **Fase 2:** **Previsão do tempo → código S/L/C** consulta a Open-Meteo e mostra o código para
     colar no Monitor Serial do Wokwi; **Regressão logística (R)**; o circuito aparece ao lado.
   - **Fase 3:** **Consultar o Oracle** roda o `consulta.sql` e mostra as 7 tabelas; **Iniciar/Parar**
     a dashboard da Fase 3 (porta 8502), com link.
   - **Fase 4:** **Iniciar/Parar** a API (porta 8000), com link para a documentação.
   - **Fase 6:** envie uma foto ou escolha uma amostra, ajuste a confiança e clique em **Detectar**;
     aparecem a imagem com as caixas, a contagem de tratores e vacas e a ação sugerida. Na primeira
     vez o YOLOv5 é baixado e demora mais.
   - **Alerta na AWS:** o botão existe, mas avisa que o serviço está em construção (frente 04).

Quando um serviço falha, o bloco mostra o código de saída e os detalhes num expansor. Os serviços
iniciados em segundo plano gravam o log em `.<serviço>.log` na raiz (ignorado pelo git) e param
junto quando a dashboard é encerrada com Ctrl+C.

### 4. Alerta no floci, a AWS local (frente 04, parte local concluída)

```bash
docker compose up -d                          # floci na porta 4566 (SNS, SQS...)
python3 main.py alerta-floci preparar         # cria o tópico farmtech-alertas + fila SQS assinante
#   -> copie o ARN impresso para SNS_TOPIC_ARN no .env (no floci é sempre
#      arn:aws:sns:us-east-1:000000000000:farmtech-alertas); deixe AWS_ENDPOINT_URL=http://localhost:4566
python3 main.py alerta                        # última leitura real de SOIL_DATA -> regras -> publica
python3 main.py alerta --simular seco         # leitura de exemplo (seco | acido | alcalino | npk | tudo | ok)
python3 main.py alerta --simular tudo --forcar --dry-run   # só mostra o e-mail, sem publicar
python3 main.py alerta --ultimas 5 --fonte api            # 5 leituras pela API da Fase 4 (API no ar)
python3 main.py alerta --simular ok --yolo fase6/saidas/<resultado>.json   # inclui a detecção do YOLO
python3 main.py alerta-floci ler              # mensagens que chegaram na fila = prova de entrega
cd alerta && uv run pytest -q                 # 9 testes das regras
```

- A saída é um JSON com as leituras avaliadas, os alertas (problema, ação, valor), o e-mail
  montado, o destino (floci ou Amazon SNS) e o `message_id`.
- A mesma condição não é reenviada em menos de 60 minutos (`alerta/.estado.json`); use `--forcar`
  para repetir, ou `--intervalo-min 0`.
- Na dashboard, bloco **Alerta na AWS**: escolha "últimas leituras do Oracle" ou uma simulação,
  marque "Forçar reenvio" se precisar e clique em **Verificar sensores e alertar**.
- `python3 main.py alerta-floci limpar` remove tópico e fila; `docker compose down` para o floci.

### 5. Publicar na AWS real (depende da sua conta)

O código não muda: basta trocar o destino no `.env`. O roteiro completo, com os prints que o
README precisa, está em [`docs/plano-entrega/04-alerta-aws.md`](docs/plano-entrega/04-alerta-aws.md).
Em resumo:

1. Conta AWS + **Zero spend budget** (Billing → Budgets), região **us-east-1**.
2. **SNS → Create topic** `farmtech-alertas` → **Create subscription** (Email) → confirmar pelo
   link que chega no e-mail.
3. **IAM**: política só com `sns:Publish` no ARN do tópico; usuário `farmtech-alerta` com essa
   política; criar access key.
4. No `.env`: `SNS_TOPIC_ARN=<ARN do console>`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` e
   **comentar** `AWS_ENDPOINT_URL`.
5. `python3 main.py alerta --simular seco --forcar` → o e-mail chega. Prints em `docs/imagens/aws/`
   e legendas no README.

### 6. Ir Além 2: notebook do algoritmo genético (concluído)

```bash
cd IR-ALEM/ir-alem-2
uv sync                                                    # numpy, pandas, matplotlib, jupyter
uv run jupyter lab ir_alem_2_algoritmo_genetico.ipynb      # abrir; "Run all" leva ~20 s
uv run jupyter nbconvert --to notebook --execute --inplace ir_alem_2_algoritmo_genetico.ipynb   # ou executar direto
```

- O notebook já está executado no repositório, com tabelas e figuras; não precisa rodar para ler.
- A entrada é `dados/talhoes.csv`. Só rode `uv run python gerar_dados.py` se quiser regerá-la a
  partir do Oracle (usa o `.env` da raiz); isso muda os números do notebook.
- As células vivem em `construir_notebook.py`; para alterar o notebook, edite esse arquivo, rode-o e
  execute o `nbconvert` acima.
- Resumo, resultados e figuras em [`IR-ALEM/README.md`](IR-ALEM/README.md). Falta só gravar o vídeo
  de até 4 minutos.

### 7. Ir Além 1: Rekognition (código pronto; rodar na AWS)

```bash
# .env da raiz com as chaves do usuário IAM (permissão rekognition:DetectLabels) e AWS_ENDPOINT_URL comentado
python3 main.py ir-alem-1 --comparar          # 4 amostras da Fase 6 -> IR-ALEM/ir-alem-1/resultados/
python3 main.py ir-alem-1 --pasta fotos       # outra pasta de jpg/png
```

Gera um JSON por foto, a imagem com as caixas do Rekognition e, com `--comparar`, o `comparacao.md`
com o YOLO da Fase 6 lado a lado. Com o floci no `.env` o script roda, mas os rótulos são falsos; por
isso `resultados/` só deve ser commitada depois da execução real. A lista de prints e a justificativa
crítica estão em [`IR-ALEM/README.md`](IR-ALEM/README.md).

### 8. Cronograma do que depende de você

Tudo o que falta (AWS, prints, vídeos, entrega) está em sessões de 30 a 90 min, com caixas para marcar,
em [`docs/plano-entrega/cronograma-aws.md`](docs/plano-entrega/cronograma-aws.md).

### 9. Rodar as demais fases

Os comandos de cada fase estão na seção "Como executar" do [`README.md`](README.md#-como-executar)
e os detalhes técnicos em [`docs/fases/`](docs/fases/).

## O que foi alterado

### 10/11/2026 — Ir Além 1 executado na AWS real, roteiros dos vídeos e região us-east-2

| Arquivo | Mudança |
|---|---|
| `IR-ALEM/ir-alem-1/resultados/` | **Resultado real** de `main.py ir-alem-1 --comparar` (Rekognition em us-east-2): JSON por foto, imagens anotadas, `resumo.json` e `comparacao.md`. Rekognition 4/4 (81–99,9 %), YOLO 4/4 (60–84 %); Rekognition sem caixa no trator. |
| `IR-ALEM/README.md` | Justificativa crítica com os números reais e o achado da localização do trator. |
| `docs/plano-entrega/roteiros-videos.md` | **Novo.** Roteiros com tempos dos três vídeos (principal 10 min, Ir Além 1 e 2 com 4 min) e a preparação comum. |
| `alerta/lambda_function.py` | Arquivo único para a Lambda (regras + handler), criado depois do `NameError` no console. |
| `.env` (local) e `.env.example` | Região da entrega é **us-east-2** (Ohio); removida a linha duplicada de `SNS_TOPIC_ARN` do floci. |
| `docs/plano-entrega/04-alerta-aws.md`, `cronograma-aws.md`, `06-ir-alem.md` | Região `us-east-2`, passos da Lambda e do Rekognition marcados como feitos. |
| Apresentação "Rekognition vs YOLO FarmTech" | Slides (artefato do Claude, 7 slides) com as imagens anotadas lado a lado, para usar no vídeo do Ir Além 1. |

### 09/11/2026 — Ir Além 1 (código) e cronograma da AWS

| Arquivo | Mudança |
|---|---|
| `IR-ALEM/ir-alem-1/pyproject.toml`, `uv.lock` | **Novo** projeto uv: boto3, pillow, python-dotenv, matplotlib. |
| `IR-ALEM/ir-alem-1/rekognition.py` | **Novo.** `DetectLabels` em cada foto da pasta, JSON completo, imagem anotada com as caixas, tradução dos rótulos para vaca/trator e `--comparar` com o YOLO da Fase 6 (`resultados/comparacao.md`). Testado no floci só para validar a chamada. |
| `IR-ALEM/ir-alem-1/figura_arquitetura.py`, `figuras/01-arquitetura.png` | **Novos.** Figura autoral. |
| `IR-ALEM/ir-alem-1/resultados/` | Vazia (`.gitkeep`) até a execução na AWS real; `resultados/yolo/` ignorada. |
| `IR-ALEM/README.md` | Seção do Ir Além 1: arquitetura, arquivos, como executar, tabela de prints com os campos do console explicados e justificativa crítica. |
| `main.py` | Serviço `ir-alem-1`. |
| `docs/plano-entrega/cronograma-aws.md` | **Novo.** Seis sessões com caixas: conta/IAM, SNS + alerta real, Lambda, Rekognition, evidências, vídeos e entrega. Política IAM única para SNS e Rekognition. |
| `docs/plano-entrega/06-ir-alem.md`, `README.md` (raiz) | Status do Ir Além 1, árvore, serviço e versão 0.7.0. |

### 09/11/2026 — Ir Além 2: algoritmo genético para o plano de manejo

| Arquivo | Mudança |
|---|---|
| `IR-ALEM/ir-alem-2/pyproject.toml`, `uv.lock` | **Novo** projeto uv: numpy, pandas, matplotlib, jupyterlab, nbformat, nbconvert, oracledb, python-dotenv. |
| `IR-ALEM/ir-alem-2/gerar_dados.py` | **Novo.** Lê as 20 leituras mais recentes de `SOIL_DATA`, sorteia a área de cada talhão (semente 42) e grava `dados/talhoes.csv`. |
| `IR-ALEM/ir-alem-2/construir_notebook.py` | **Novo.** Células do notebook em texto; gera o `.ipynb`. |
| `IR-ALEM/ir-alem-2/ir_alem_2_algoritmo_genetico.ipynb` | **Novo, executado.** Problema (mochila binária de intervenções com orçamento), normalização das escalas de N/P/K (0–100 e 0–255), itens com custo e benefício, AG do zero (torneio/roleta, um ponto/uniforme, bit-flip/troca, elitismo, penalidade + reparo), validação com força bruta e gulosa, 8 configurações × 10 sementes, plano final, figura autoral, parâmetros e conclusões. |
| `IR-ALEM/ir-alem-2/dados/talhoes.csv`, `plano_escolhido.csv` | Entrada reprodutível e saída do plano. |
| `IR-ALEM/ir-alem-2/figuras/*.png` | Arquitetura, convergência, efeito dos operadores, qualidade × tempo e plano por talhão. |
| `IR-ALEM/README.md` | **Novo.** Índice dos dois desafios, resumo e resultados do Ir Além 2, como executar. |
| `README.md` | Status dos Ir Além, árvore de pastas e versão 0.6.0. |
| `docs/plano-entrega/06-ir-alem.md`, `README.md` | Ir Além 2 marcado como pronto (falta o vídeo); nota sobre o Rekognition no floci. |

Resultado da execução de 09/11/2026: na instância reduzida o AG igualou a força bruta; na completa,
24 intervenções com 100 % do orçamento e 99,8 % da heurística gulosa; torneio venceu roleta em todas as
combinações, cruzamento e mutação diferiram pouco. Um problema corrigido no caminho: com penalidade
proporcional, o melhor indivíduo podia estourar o orçamento por poucos reais; o reparo final (remove os
itens de pior benefício/custo até caber) garante um plano viável.

### 08/11/2026 — Frente 04 (parte local): serviço de alerta testado no floci

| Arquivo | Mudança |
|---|---|
| `alerta/pyproject.toml`, `uv.lock` | **Novo** projeto uv da Fase 7: boto3, oracledb, python-dotenv, requests; pytest no grupo dev. |
| `alerta/regras.py` | **Novo.** Regras como funções puras (umidade < 60 %, pH fora de 6,0–6,8, N/P/K < 30 %, vaca detectada) e montagem do e-mail. |
| `alerta/alerta.py` | **Novo.** Serviço: lê leituras (Oracle, API, simulação ou JSON), aplica as regras, evita repetição em 60 min, publica no SNS via boto3 (floci quando `AWS_ENDPOINT_URL` existe) e imprime JSON. Código 4 quando havia alertas e a publicação falhou. |
| `alerta/floci.py` | **Novo.** `preparar`, `ler` e `limpar` o tópico SNS e a fila SQS do floci. |
| `alerta/test_regras.py` | **Novo.** 9 testes das regras (`uv run pytest`). |
| `alerta/lambda_function.py` | **Novo (10/11/2026).** Arquivo único para colar no console da AWS Lambda: `regras.py` + `lambda_handler` que publica no `SNS_TOPIC_ARN`. Testado localmente com um cliente SNS falso. |
| `alerta/.gitignore` | `.venv/`, caches e `.estado.json`. |
| `main.py` | `alerta` deixa de ser placeholder; novo `alerta-floci`. Código 4 do alerta não é tratado como erro. |
| `fase4/src/paginas/central.py` | Bloco "Alerta na AWS" completo: fonte (Oracle ou simulação), quantidade de leituras, "Forçar reenvio", tabela de alertas, status da publicação e o e-mail montado. |
| `.env.example` | Bloco AWS: `AWS_REGION`, `SNS_TOPIC_ARN`, `AWS_ENDPOINT_URL` (floci) e as chaves comentadas para a AWS real. |
| `README.md` | Seção "Serviço de alertas na AWS" reescrita (arquitetura, regras, floci, AWS pendente), status, diagrama, árvore, serviços e versão 0.5.0. |
| `docs/plano-entrega/04-alerta-aws.md` | Parte local marcada como feita, decisão dos 30 % de N/P/K e o **passo a passo da AWS real** com os prints esperados. |
| `docs/plano-entrega/README.md` | Situação do critério 6 e lista "Já feito". |

Testes em 08/11/2026 contra o floci 2.4.0: a última leitura real do Oracle (umidade 50 %, pH 7,0,
N 25, P 0, K 0) gerou 5 alertas e a mensagem apareceu na fila SQS; simulações, `--dry-run`,
`--forcar`, `--yolo` com o JSON do `detect.py` e o bloqueio de repetição; botão da dashboard com o
`AppTest`. O envio de e-mail de verdade só acontece na AWS real.

### 08/11/2026 — Frente 03: Central de serviços na dashboard da Fase 4

| Arquivo | Mudança |
|---|---|
| `fase4/src/app.py` | **Reescrito.** Agora só configura a página e a navegação (`st.navigation`) entre as três páginas; carrega o `.env` da raiz. |
| `fase4/src/paginas/analise_solo.py` | **Movido** de `app.py`. É a dashboard original da Fase 4; só saíram o `set_page_config` (que ficou no `app.py`) e mudou o título. Comportamento igual. |
| `fase4/src/paginas/inicio.py` | **Novo.** Estado dos serviços (`.env`, API, Oracle, AWS) e tabela das fases. |
| `fase4/src/paginas/central.py` | **Novo.** Blocos das Fases 1, 2, 3, 4, 6 e do alerta, com formulário, botões, tabelas e imagens. |
| `fase4/src/core/servicos.py` | **Novo.** Ponte com o `main.py`: `rodar()` executa um serviço e devolve stdout/stderr; `iniciar()`/`parar()` cuidam dos serviços que ficam no ar (grupo de processos próprio, log em `.<serviço>.log`); verificações de `.env`, API, porta do Oracle e AWS. |
| `.gitignore` (raiz) | Ignora `/.*.log`, os logs dos serviços em segundo plano. |
| `README.md` | Status "dashboard por botão" concluído, arquitetura com o `main.py` entre a dashboard e as fases, árvore de pastas e versão 0.4.0. |
| `docs/fases/fase4.md` | Seção "Dashboard central (Fase 7)" com as páginas. |
| `docs/plano-entrega/03-dashboard-central.md`, `README.md` | Frente concluída; só os prints ficaram para a frente 05. |

Testes em 08/11/2026 com o `AppTest` do Streamlit (sem navegador): as três páginas abrem sem
exceção; na Central, o cálculo da Fase 1 (manga, 20.000 m² e 1.000 L), o código S/L/C da Fase 2,
as 7 consultas da Fase 3, a detecção da Fase 6 em `vaca_02.jpg` (1 vaca e a ação sugerida) e o aviso
do alerta. Iniciar/Parar da dashboard da Fase 3 testado pela ponte (`servicos.py`): a porta 8502
abre e fecha. A dashboard central também subiu pelo `main.py fase4-dashboard` (na porta 8503, porque
a 8501 estava ocupada nesta máquina). Os botões em R não foram exercitados (R não instalado aqui).

### 08/11/2026 — Frente 02: `main.py` dispara cada serviço pelo terminal

| Arquivo | Mudança |
|---|---|
| `main.py` | **Novo.** Registro dos 12 serviços (nome, descrição, pasta, comando, pré-requisitos). `listar` mostra a tabela; `<serviço> [args]` confere `uv`/`Rscript`/`.env`, roda o comando na pasta da fase com `uv run --project` e devolve o código de saída. Caminhos relativos nos argumentos viram absolutos. `alerta` fica registrado como "em construção" até a frente 04. |
| `fase1/src/calculo.py` | **Novo.** Cálculo da Fase 1 sem `input()`: `--cultura manga` (largura, comprimento, ruas, litros por metro) ou `--cultura cana` (raio, kg por m²). Imprime JSON com área e insumo; `--salvar` acrescenta o registro no `farm_tech_solutions.csv`, com o mesmo formato do programa interativo. Reutiliza as funções de área de `farm_math_handler.py`. |
| `fase3/consultas.py` | **Novo.** Lê `fase3/consulta.sql`, executa cada consulta no Oracle (credenciais do `.env` da raiz) e imprime as tabelas no terminal; `--json` devolve tudo em JSON para a dashboard; `--sql` aceita outro arquivo. Roda no ambiente de `fase3/dashboard`, que já tinha `oracledb` e `python-dotenv`. |
| `README.md` | Seção "Disparar os serviços pelo terminal" com a tabela de serviços; a tabela antiga virou "Rodar cada fase diretamente"; status, árvore de pastas e versão 0.3.0. |
| `docs/plano-entrega/02-cli-main.md` | Frente concluída, com o resultado do teste de cada serviço e as decisões. |
| `docs/plano-entrega/03-dashboard-central.md` | A tarefa "Fase 1 sem `input()`" ficou pronta aqui. |
| `docs/plano-entrega/README.md` | Situação do critério 5, lista "Já feito" e ordem de execução. |

Testes feitos em 08/11/2026: `listar`, serviço inexistente, `alerta`, `fase1-calculo` (manga, cana,
argumento faltando e `--salvar`), `fase2-clima` (Open-Meteo respondeu "C"), `fase3-consultas`
(7 consultas, 22 linhas em `SENSOR_DADOS`), `fase3-dashboard` (porta 8502 respondeu), `fase4-api`
(na porta 8001, porque a 8000 estava ocupada nesta máquina por outro programa) e `fase6` com
caminho relativo e absoluto. Os três serviços em R não puderam rodar porque o R não está instalado
aqui; a mensagem "`Rscript` não encontrado" foi testada.

Problemas encontrados e como foram resolvidos:

- **Caminho relativo da imagem sumia:** o `main.py` roda a Fase 6 dentro de `fase6/`, então
  `fase6/data/amostras/foto.jpg` deixava de existir lá. Os argumentos que são caminhos existentes
  agora viram absolutos antes de rodar.
- **Porta 8000 ocupada:** o erro "address already in use" vem do uvicorn; basta passar `--port`.

### 08/11/2026 — Frente 01: Fase 6 vira serviço de detecção

| Arquivo | Mudança |
|---|---|
| `fase6/src/detect.py` | **Novo.** Carrega `models/best.pt` com o YOLOv5 no commit do treino (`f9578796`), detecta numa imagem, grava a imagem anotada em `fase6/saidas/` e imprime um JSON com detecções, resumo por classe e ações sugeridas para o alerta da AWS. Na 1ª execução clona o YOLOv5 em `fase6/.trabalho/yolov5/`. |
| `fase6/data/amostras/*.jpg` | **Novos.** 4 fotos do Wikimedia Commons (2 tratores, 2 vacas) que o modelo reconhece com confiança entre 0,61 e 0,84. O dataset original ficou no Google Drive e não estava acessível. |
| `fase6/data/amostras/LICENCAS.md` | **Novo.** Título, autoria, link e licença (CC0, CC BY 2.0, domínio público) de cada foto. |
| `fase6/pyproject.toml` | `uv sync` passa a instalar só o necessário para a detecção, com **PyTorch para CPU** (índice `download.pytorch.org/whl/cpu` em Linux e Windows). TensorFlow, scikit-learn e Jupyter foram para o grupo `notebook`, que não entra por padrão (`default-groups = []`). Adicionados `gitpython` e `tqdm`, exigidos pelo YOLOv5. O ambiente caiu de vários GB para ~1,5 GB. |
| `fase6/uv.lock` e `fase6/requirements.txt` | Regenerados a partir do novo `pyproject.toml`. |
| `fase6/.gitignore` | `saidas/` (imagens anotadas) passa a ser ignorada. |
| `docs/fases/fase6.md` | Seção nova sobre o `detect.py`, as amostras e o ambiente; "Como executar" atualizado. |
| `docs/plano-entrega/01-fase6-deteccao.md` | Frente marcada como concluída, com as decisões tomadas. |
| `docs/plano-entrega/README.md` | Situação do critério 5 e lista "Já feito" atualizadas. |
| `README.md` | Linha de status da Fase 6, comando novo em "Como executar", árvore de pastas e versão 0.2.0 no histórico. |
| `COMO_USAR.md` | **Novo.** Este arquivo. |

Problemas encontrados e como foram resolvidos:

- **`No module named 'pathlib._local'`** ao carregar o `best.pt`: o arquivo foi salvo no Colab com
  Python 3.13, e esse módulo não existe no Python 3.12 do projeto. O `detect.py` registra
  `sys.modules["pathlib._local"] = pathlib` antes do `torch.hub.load`.
- **Logs do YOLOv5 no stdout** ("Fusing layers...", resumo do modelo) misturados ao JSON: o script
  redireciona o stdout para o stderr durante o carregamento e aponta o logger `yolov5` para o stderr.
- **Fotos genéricas com confiança baixa:** de 28 fotos do Commons testadas, 7 ficaram abaixo de 0,25
  e uma gerou falso positivo. Efeito esperado de um treino com 32 fotos por classe; as 4 amostras
  foram escolhidas entre as reconhecidas com folga. Vale citar na discussão crítica do vídeo.
- **`pip` ausente no ambiente do uv:** o YOLOv5 tenta instalar dependências que faltam; o script
  define `YOLOv5_AUTOINSTALL=False` para ele só avisar.

### 08/11/2026 — Consolidação inicial (versão 0.1.0)

- Fases 1 a 6 reunidas em `fase1/` … `fase6/`; repositório Git aninhado da Fase 1 removido;
  AgriShield (`globalSolutions/`) retirado da raiz (continua no histórico, commit `234fb73`).
- `.env` único na raiz com `ORACLE_USER`, `ORACLE_PASSWORD` e `ORACLE_DSN`; a Fase 4 passou a ler
  essas variáveis. `.env.example` e `docker-compose.yaml` (floci) na raiz.
- Pastas das fases saneadas: READMEs, modelos de template, `.txt` e arquivos sem uso removidos; o
  conteúdo útil foi para `docs/fases/` e `docs/imagens/`. O campo `readme` saiu de 4 `pyproject.toml`.
- `fase1/src/farm_tech_solutions.csv` passou a ser versionado (o script R depende dele) e o script
  R lê o CSV a partir de `fase1/src`.
- `fase6/models/best.pt` recuperado do Google Drive e conferido.
- `README.md` integrado e `docs/plano-entrega/` com as frentes 01 a 06.

## Próximos passos

Na ordem do plano: a parte da AWS real da [04 — alerta na AWS](docs/plano-entrega/04-alerta-aws.md)
(passo 5 acima) e
[05 — documentação, vídeo e entrega](docs/plano-entrega/05-documentacao-video-entrega.md).
Antes da entrega, tornar o repositório **privado** e adicionar `fiap-tutoria`.
