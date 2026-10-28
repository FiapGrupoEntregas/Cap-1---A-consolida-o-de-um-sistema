# Roteiro de testes do MVP — com a IA como fio condutor

> **Para que serve este documento.** É um cardápio, não uma obrigação. São **12 blocos** de teste
> que percorrem o produto inteiro. Leia, escolha os que você vai mostrar e ignore o resto — no fim
> há três montagens sugeridas (vídeo de 5 min, demo ao vivo, defesa técnica).
>
> Cada bloco tem a mesma estrutura: **o que fazer · o que tem de acontecer · o que isso prova sobre
> IA · print que sai daqui**.
>
> A matéria é **IA**, e este projeto tem uma tese sobre IA que precisa ser dita antes de qualquer
> tela. Ela está na [Parte 0](#parte-0-a-tese-de-ia-do-projeto). Sem ela, metade dos blocos abaixo
> parece "um sistema que não usa IA", quando na verdade é **um sistema que usa IA no lugar certo**.

---

## Parte 0: a tese de IA do projeto

Há **três camadas de decisão** no AgriShield, e só uma delas decide. Isso não é limitação: é o
argumento.

| Camada | O que é | Aprende? | Decide o alerta? |
|---|---|---|---|
| **Motor de regras** | Limiares de chuva, vento, inclinação e solo, calibrados à mão | ❌ | ✅ **sim** |
| **Modelo preditivo** | Regressão logística treinada em 2.256 apólices reais do PSR | ✅ | ❌ informa a seguradora |
| **Experimento MLP** | Rede neural (8 neurônios, 1 camada), desligada por padrão | ✅ | ❌ nada |

**A frase que sustenta a apresentação inteira:**

> *"Nós treinamos um modelo, medimos, ele venceu o baseline — e mesmo assim não deixamos ele decidir
> o alerta. Vou mostrar o número que explica por quê."*

E o número é este: a variável que mais pesa no modelo é **`state`, a unidade federativa**, com
importância **0,0276** — quatro vezes a segunda colocada (`aspect_label`, 0,0066). O modelo aprendeu
**geografia de perda agrícola**, não física de capotamento. Um modelo que decide pela UF não pode
dizer a um operador se *esta encosta, hoje*, é segura.

> Isso é o oposto de uma confissão de fraqueza. É a demonstração de que o grupo **mediu**, **leu o
> resultado** e **escolheu a arquitetura a partir da evidência** — que é exatamente o que se espera
> de quem trabalha com IA.

### Os números que você pode citar de cabeça

| Fato | Valor | Onde conferir na hora |
|---|---|---|
| Linhas do dataset | **2.256** | ficha `data/dataset_treino.json` |
| Divisão temporal | treino ≤2021 **1.447** · validação 2022–23 **504** · teste 2024 **305** | metadado do modelo |
| Variáveis usadas | **22** (11 descartadas de propósito) | `risk_model_v1.json` |
| AUC-PR no teste — baseline por regras | **0,074** | cartão na tela |
| AUC-PR no teste — regressão logística | **0,144** | cartão na tela |
| AUC-PR no teste — floresta aleatória | **0,196** | `dados-e-modelo.md` |
| Diferença modelo − baseline | **+0,070**, IC 95% **[+0,003, +0,169]** | `risk_model_v1.json` |
| Sinistros no teste | **26** — abaixo dos 30 que o projeto exige | cartão na tela |

---

## Preparação (5 minutos, faça antes)

```bash
cp docker/.env.example .env          # escolha uma chave em AGRISHIELD_API_KEY
docker compose up -d --build
docker compose run --rm api python scripts/load_psr.py --sample
```

**Confira antes de gravar qualquer coisa:**

```bash
curl -s localhost:8000/api/v1/health                      # {"status":"ok",...}
curl -s localhost:8000/api/v1/farms | head -c 80          # as 3 fazendas
curl -s localhost:8000/api/v1/reports/crop | head -c 80   # relatórios com dados
```

> ⚠️ **O mapa depende da cota diária da Open-Meteo**, que vira às 00:00 UTC (21:00 em Brasília).
> Se `/farms/{id}/risk` responder **503**, a cota acabou e nenhuma tela de mapa vai funcionar.
> Teste isto **antes** de montar a gravação:
> ```bash
> curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/api/v1/farms/cafe-carmo-de-minas/risk
> ```
> `200` é seguir. `503` é esperar a virada da cota.

---

## Bloco 1 — O relevo é dado real, não desenho

**Fazer:** abrir **Mapa de risco** → aba **Relevo**, fazenda *Sítio Café da Serra* (Carmo de Minas).
Passar o mouse por uma célula da encosta e por uma do fundo de vale.

**Esperado:** grade 10 × 10 colorida por inclinação; o tooltip mostra inclinação em graus,
orientação e classe de terreno; os KPIs no topo mostram a área íngreme em %.

**O que prova sobre IA:** que a **entrada** do sistema é real. Antes de falar de modelo, é preciso
mostrar que os dados não são inventados — a elevação vem do Copernicus DEM via Open-Meteo, e a
inclinação é calculada por diferença de elevação entre células vizinhas, não estimada.

**Print:** #1 (mapa de relevo com KPIs e legenda).

---

## Bloco 2 — A mesma encosta muda de cor com o clima

**Fazer:** aba **Previsão de risco**. Percorrer os 7 dias na faixa superior e parar num dia
🔴. Abrir o painel do dia e ler os motivos.

**Esperado:** o mapa recolore entre os dias; um dia vermelho traz motivos com número
(*"42 mm de chuva em 72 h: solo encharcado"*), e o limite de inclinação do dia cai de 15° para 10°.

**O que prova sobre IA:** aqui está o **contraste central**. Esta decisão é de **regras**, e cada
alerta carrega o número que o disparou. Diga em voz alta: *"nenhum modelo participou desta tela — e
é por isso que eu consigo te explicar cada cor"*. É o gancho para o Bloco 7.

**Print:** #2 (previsão de 7 dias com dia vermelho aberto e motivos à vista).

---

## Bloco 3 — O contraste entre duas fazendas

**Fazer:** trocar a fazenda no seletor lateral para *Grãos Sorriso* (MT) e voltar para
*Carmo de Minas* (MG), no mesmo dia.

**Esperado:** Sorriso é plana e quase toda verde; Carmo de Minas tem encostas e células vermelhas.

**O que prova sobre IA:** que o sistema **discrimina** — no sentido estatístico. Se as duas fazendas
parecessem iguais, o relevo não estaria fazendo nada no modelo mental do produto.

**Print:** #3 (as duas lado a lado, mesmo dia).

---

## Bloco 4 — O cenário simulado, rotulado como simulado

**Fazer:** ligar o toggle **"Simular chuva forte"** e observar o mapa e o limite.

**Esperado:** as células pioram, o limite cai — e aparece um aviso de que o cenário é **simulado**.

**O que prova sobre IA:** honestidade de dados. O projeto distingue dado real de dado simulado **na
tela**, não só no código. Numa matéria de IA isso vale nota: é o princípio de nunca apresentar
sintético como observado.

---

## Bloco 5 — O limite viaja até a máquina

**Fazer:** ir a **Equipamento ao vivo**, ver o card do limite do dia e clicar em
**Enviar ao equipamento**. Com o Wokwi aberto, ver o Serial do ESP32.

**Esperado:** confirmação do envio na tela; no Serial, `[config]` com o novo limite e
`limit_applied` publicado de volta.

**O que prova sobre IA:** que a saída do raciocínio **fecha o ciclo** num atuador. Sistemas de IA que
só produzem relatório são fáceis; este produz uma **ação** num dispositivo, com confirmação de volta.

**Print:** #4 (card do limite + confirmação de envio).

---

## Bloco 6 — O dispositivo decide sozinho, sem internet

**Fazer:** no Wokwi, mover o MPU6050 para ~12° e depois para 60°.

**Esperado:** 12° → LED vermelho + buzzer + evento `tilt_alert`; 60° por ~3 s → **capotamento**, com
os 30 s de contexto anteriores no evento. O painel web mostra o banner de capotamento.

**O que prova sobre IA:** **inferência na borda**. O ESP32 aplica o limite recebido usando
`max(|roll|, |pitch|)` com média móvel de 5 amostras — decisão local, sem rede. É o argumento de
resiliência: a inteligência não pode depender de conectividade quando a consequência é um
capotamento.

**Prints:** #5, #6 e #7 (painel com telemetria, banner de capotamento com o gráfico dos 30 s, e o
alerta local no Wokwi com LED/buzzer/OLED).

---

## Bloco 7 — 🧠 O modelo preditivo: o bloco mais importante para a matéria

**Fazer:** voltar ao **Mapa de risco** → **Previsão de risco** e rolar até o cartão
**"Probabilidade de sinistro (modelo)"**. Ler o cartão **inteiro**, de cima a baixo.

**Esperado, e é isto que você vai narrar:**

1. a **probabilidade** do dia;
2. *"Treinado em: …"* — o contexto do treino;
3. *"**AUC-PR no teste: 0,144** contra **0,074** do baseline por regras (26 sinistros em 305
   linhas)"*;
4. a **ressalva**, montada em tempo de execução a partir do próprio artefato do modelo;
5. **"O que mais pesa no modelo, em geral"**, com as variáveis e suas importâncias.

**O que prova sobre IA — quatro coisas, em ordem:**

- **Há aprendizado de máquina de verdade.** Regressão logística treinada em 2.256 apólices reais do
  PSR/SISSER, 22 variáveis, com `ColumnTransformer` (imputação + escala + one-hot).
- **A avaliação é metodologicamente correta.** Divisão **temporal** (treino ≤2021, validação
  2022–23, teste 2024), não aleatória — porque dados de safra têm tempo, e embaralhar vazaria o
  futuro para o passado. O limiar foi escolhido **na validação** e aplicado sem ajuste no teste.
- **A incerteza é declarada.** Diferença de +0,070 com IC 95% de **[+0,003, +0,169]**, por bootstrap
  pareado de 10.000 reamostragens. O intervalo **quase toca o zero** — e isso está escrito, não
  escondido.
- **A tela nunca discorda do modelo.** A ressalva não é texto fixo: é montada a partir do artefato
  carregado. Trocar o modelo muda a frase sozinha.

> **Momento-chave da apresentação.** Aponte para a lista de importâncias e diga: *"a variável que
> mais pesa é o **estado**. O modelo aprendeu onde há perda agrícola no Brasil — seca no Nordeste,
> geada no Sul. Isso é útil para a seguradora precificar carteira. Mas não serve para dizer a um
> operador se **esta encosta, hoje**, é segura. Por isso o alerta é por regras."*

**Print:** #11 (cartão do score híbrido, com a ressalva legível).

---

## Bloco 8 — 🧪 A rede neural, e por que ela não está no caminho

**Fazer:** ligar o toggle **"Mostrar score experimental da MLP"**. Ele começa **desligado**.

**Esperado:** aparece um cartão **"Score experimental da MLP"** com o score (0–1), a versão do
artefato e a ressalva *"não é uma probabilidade calibrada"*.

**O que prova sobre IA:** que o grupo **tentou rede neural e reportou o resultado honesto**.

Os números para citar:

| Modelo | AUC-PR no teste (2024) |
|---|---|
| Baseline por regras | 0,074 |
| Regressão logística (publicado) | **0,144** |
| **MLP (8 neurônios, 1 camada)** | **0,150** |
| Floresta aleatória | 0,196 |

A MLP **empatou** com a logística — a diferença está dentro do ruído de um teste com 26 sinistros.
Por isso entrou como experimento isolado: artefato separado, opt-in na API, toggle desligado na
tela, e **zero** participação em nível, limite ou alerta.

> *"Um experimento negativo documentado vale mais que um modelo bonito usado onde não devia."*

**Pergunta provável da banca — e a resposta:** *"por que não usaram a floresta aleatória, que teve
0,196?"* Porque **o teste não seleciona modelo**. A escolha se deu na validação, onde a floresta
ficou **−0,0045** abaixo, contra um erro padrão de **0,0190**: empate técnico, e pela regra de um
erro padrão vence o candidato mais simples e explicável. Trocar por causa do teste seria usar o
conjunto final para decidir — e aí o número dele deixaria de significar qualquer coisa. Está escrito
em [dados-e-modelo.md](dados-e-modelo.md).

---

## Bloco 9 — O perfil de terreno para subscrição

**Fazer:** abrir **Subscrição**.

**Esperado:** selo de classe **A/B/C**, score 0–100, indicadores do relevo, drivers e a carteira
ordenada. Em destaque, a **nota de calibração**.

**O que prova sobre IA:** *feature engineering* aplicada a negócio. O score 0–100 não vem de modelo:
é composição ponderada de indicadores de relevo, e a tela **declara que os pesos são da v1 e não
foram calibrados** com base de sinistros. Declarar que um score não está calibrado é maturidade —
muita gente publica número sem isso.

**Print:** #9.

---

## Bloco 10 — Relatórios e tendências

**Fazer:** abrir **Relatórios** e percorrer as três abas: **Equipamento**, **Região** e **Cultura**.
Baixar um CSV.

**Esperado:** cada aba traz o campo `purpose` (para quem serve e que decisão apoia), gráfico de
tendência e botão de CSV gerado pela API.

**O que prova sobre IA:** que a saída é **legível por perfil**, que é o que o enunciado pede. E há
uma ressalva a dizer em voz alta: o enunciado pede recortes por *"equipamento, região ou tipo de
operação"* — a base PSR traz **cultura**, não tipo de operação, e a tela diz isso.

**Print:** #10 (uma captura por aba).

---

## Bloco 11 — Replay: o teste mais honesto do produto

**Fazer:** abrir **Replay de acidentes**, escolher o caso de **Imbituva** e ler o veredito, a fonte
da notícia e a faixa *"O que este replay não prova"*. Depois olhar o placar do topo.

**Esperado:** placar **2 de 5 no ponto**, 3 de 5 na vizinhança. Em Imbituva, o motor apontou risco de
raio no dia em que um raio matou.

**O que prova sobre IA:** **validação retrospectiva contra a realidade**, que é raro num trabalho de
graduação. E o placar **não** é 5 de 5 — os três "não" ficam à vista, com o motivo (incêndio por
falha mecânica não é o que este motor promete detectar).

> Se você quiser um único momento que demonstre maturidade, é este. Mostrar um placar 2/5 e explicar
> por que os outros três falharam vale mais que qualquer número redondo.

---

## Bloco 12 — Rastreabilidade: toda decisão fica registrada

**Fazer:**

```bash
curl -s -H "X-API-Key: SUA-CHAVE" "localhost:8000/api/v1/audit?limit=3" | python3 -m json.tool
curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/api/v1/audit    # sem chave → 401
```

**Esperado:** linhas de `decision_log` com entrada, saída, **versão da regra e do modelo** que
decidiram; e 401 sem a chave.

**O que prova sobre IA:** **governança de modelo**. Cada decisão registra *com qual versão de modelo
foi tomada* — é o que permite auditar um score meses depois e o que qualquer uso regulado de IA
exige. Some-se o hash SHA-256 do payload cru de cada evento, que prova que o dado gravado é o que o
equipamento publicou.

**Print:** #8.

---

## Blocos extras (se sobrar tempo ou interesse)

| Bloco | O que fazer | O que prova |
|---|---|---|
| **Cadastro de maquinário** | Cadastrar uma máquina e vincular o `tractor-01`; tentar vincular o mesmo ESP32 a outra | Escrita com chave de API, auditoria, e a recusa explicada no campo certo |
| **Degradação sem clima** | `docker compose stop` do acesso à internet, ou esperar a cota acabar | As rotas de clima devolvem **503 com mensagem em português**, e o resto continua servindo — não há tela quebrada |
| **Testes automatizados** | `cd api && uv run pytest` | 1.007 testes, todos **offline** (Open-Meteo e MQTT mockados) |
| **Reprodutibilidade** | `docker compose up` numa máquina limpa | O MVP roda fora do ambiente de quem o escreveu — exigência textual do enunciado |

---

## Três montagens sugeridas

### A. Vídeo de 5 minutos (obrigatório) — foco em IA

| Tempo | Blocos |
|---|---|
| 0:00–0:45 | Problema + Parte 0 (a tese das três camadas) |
| 0:45–1:30 | Blocos 1 e 2 (relevo real → risco explicável) |
| 1:30–2:15 | **Bloco 7** (modelo, métrica, ressalva, importâncias) |
| 2:15–2:45 | **Bloco 8** (a MLP e por que não decide) |
| 2:45–3:30 | Blocos 5 e 6 (limite viaja, dispositivo decide sozinho) |
| 3:30–4:10 | Blocos 10 e 11 (relatórios e replay) |
| 4:10–4:45 | Bloco 12 + fechamento |

### B. Demo ao vivo (~8 min)

Todos os blocos de 1 a 12, na ordem. É a ordem natural: dado real → regra → ação → modelo →
negócio → prova.

### C. Defesa técnica (se houver arguição)

Blocos **7, 8, 11 e 12**, com `dados-e-modelo.md` aberto. São os quatro que sustentam perguntas
difíceis: metodologia, experimento negativo, validação retrospectiva e governança.

---

## Se algo der errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Mapa e previsão em **503** | cota diária da Open-Meteo esgotada | Esperar as 00:00 UTC (21:00 BRT). **Não** gere dataset no dia da apresentação |
| Cartão do modelo não aparece | artefato ausente | `ls api/app/data/model/` — a API sobe sem ele, e a tela omite o cartão |
| Botão "Enviar ao equipamento" dá **401** | chave do front ≠ chave da API | Em Docker isso não acontece (uma variável alimenta as duas); fora dele, confira os dois `.env` |
| Telemetria não aparece com o Wokwi | **a API e o ESP32 em brokers diferentes** (causa mais comum, e nada na tela avisa) | `uv run --project api python scripts/diagnosticar_mqtt.py` — ele escuta os dois brokers e diz qual `.env` corrigir |
| Equipamento **oscila** entre online e offline a cada ~30 s | a aba do Wokwi perdeu o foco e o navegador a estrangulou: o ping do MQTT não sai e o broker derruba | Mantenha a aba do Wokwi **visível**. O firmware já usa keepalive de 60 s para tolerar a troca de janela; confira no Serial se o status imprime ~1 linha por segundo |
| Relatórios vazios | o banco do **container** está vazio: carregar o PSR no host não alimenta o container, são bancos diferentes | `./scripts/importar-psr-no-docker.sh` (base real) ou `docker compose run --rm api python scripts/load_psr.py --sample` (amostra) |
| Só a aba **Equipamento** zerada | ela vem de telemetria, não do PSR | deixe o ESP32 publicando alguns minutos antes de capturar |

---

## Documentos de apoio

- Método, métricas e ressalvas do modelo: [dados-e-modelo.md](dados-e-modelo.md)
- Onde há IA, em linguagem não técnica: [guia-do-projeto.md §4](guia-do-projeto.md#4-onde-há-inteligência-artificial-no-projeto)
- Limiares das regras: [regras-de-risco.md](regras-de-risco.md)
- Decisões e seus porquês: [decisoes.md](decisoes.md)
- O que capturar de tela: [evidencias/prints/README.md](evidencias/prints/README.md)
