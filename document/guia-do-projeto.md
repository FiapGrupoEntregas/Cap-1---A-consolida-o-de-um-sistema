# Guia do projeto — Sompo AgriShield

Documento único de entrada. Quem abre o repositório pela primeira vez — tutor, banca ou um
desenvolvedor novo — lê **este arquivo** e entende o que o sistema faz, como ele está montado, o
que já está implementado, por que foi implementado assim e como rodar tudo do zero.

> **Regra deste guia: número que muda mora na fonte, não aqui.**
> Métricas do modelo, limiares de risco, tamanho do dataset, contagem de testes e contagem de
> rotas **não** são copiados para cá — só apontados. Já aconteceu de um número ser corrigido no
> código e continuar errado em oito documentos; a forma de não repetir isso é não duplicá-lo.
> Onde este guia precisa citar um valor, ele cita **onde vê-lo atualizado**.
>
> Situação em **22/09/2026**. O código congela em **25/09/2026** e a entrega é em **27/09/2026**.

## Índice

1. [O problema e a solução](#1-o-problema-e-a-solução)
2. [Como o sistema está montado](#2-como-o-sistema-está-montado)
3. [O que está implementado](#3-o-que-está-implementado)
4. [Onde há inteligência artificial no projeto](#4-onde-há-inteligência-artificial-no-projeto)
5. [Como foi implementado: as decisões que explicam o código](#5-como-foi-implementado-as-decisões-que-explicam-o-código)
6. [Como executar tudo, do zero](#6-como-executar-tudo-do-zero)
7. [Como verificar que funciona](#7-como-verificar-que-funciona)
8. [Limitações declaradas](#8-limitações-declaradas)
9. [Mapa de documentos](#9-mapa-de-documentos)

---

## 1. O problema e a solução

O seguro de máquinas agrícolas no Brasil é **reativo**: a seguradora age depois do acidente. E um
dos fatores que mais pesam no risco de uma máquina — o **relevo** — praticamente não entra na
conta. Uma encosta é segura com o solo seco e perigosa depois de dias de chuva, porque o solo
perde aderência. Nas baixadas a água acumula e a máquina atola. Os topos de morro concentram raios
e as cristas expostas pegam as rajadas mais fortes. Nada disso é constante: **muda com o dia**.

O AgriShield cruza **relevo × clima** e entrega quatro coisas:

| O que entrega | Para quem | Onde aparece |
|---|---|---|
| **Mapa de risco por talhão e por dia** (7 dias à frente), com o motivo de cada alerta em números | gestor de frota, operador | tela *Mapa de risco* |
| **Limite de inclinação dinâmico na máquina**, calculado pela plataforma e aplicado por um ESP32 embarcado, que alerta o operador na hora mesmo sem internet | operador, técnico de manutenção | tela *Equipamento ao vivo* + dispositivo no Wokwi |
| **Perfil de terreno para subscrição** (classe A/B/C), sem questionário e sem hardware, e **relatórios de tendência** por equipamento, região e cultura | analista da seguradora | telas *Subscrição* e *Relatórios* |
| **Replay de acidentes reais noticiados**: o motor roda na data e no local do acidente e responde "o sistema teria alertado?" — inclusive quando a resposta é não | banca, pitch | tela *Replay de acidentes* |

Duas escolhas de fundo, que valem mais que qualquer tela:

- **O alerta ao operador vem de regras explicáveis**, com limiar documentado em
  [regras-de-risco.md](regras-de-risco.md) e o motivo escrito em português com números.
- **O modelo preditivo entra ao lado, nunca no lugar.** Ele é treinado com sinistros reais do
  seguro rural (PSR/SISSER) e dá uma segunda leitura para a seguradora. O resultado da comparação
  com o baseline por regras — com todas as ressalvas — está em
  [dados-e-modelo.md § Resultados do modelo (D3)](dados-e-modelo.md#resultados-do-modelo-d3), e é
  a **única** fonte desse número no projeto. A API monta a ressalva a partir do próprio artefato
  em tempo de execução, então a tela nunca discorda do modelo que está servindo.

## 2. Como o sistema está montado

Três camadas, uma responsabilidade cada:

| Camada | Pasta | Faz | **Não** faz |
|---|---|---|---|
| **API** | `api/` | Busca elevação e clima, calcula relevo, risco e limite do dia, fala MQTT com o equipamento, grava telemetria, eventos e decisões, expõe tudo em REST | Interface |
| **Front-web** | `front-web/` | Mapas, gráficos, painéis, downloads | Nenhuma regra de negócio; não fala MQTT nem chama a Open-Meteo |
| **Dispositivo** | `iot/` | Mede inclinação e ambiente, aplica o limite recebido, alerta o operador, detecta capotamento, publica telemetria e eventos | Não calcula risco climático; só aplica o limite que a API manda |

O fluxo do dado, de ponta a ponta:

```
Open-Meteo (elevação, previsão, histórico) ─HTTP→ api/ ─REST→ front-web/
PSR/SISSER (CSV aberto) ─script→ SQLite ─→ dataset ─→ modelo ─→ api/
api/ ←──MQTT (broker público)──→ ESP32 no Wokwi
```

O **diagrama oficial da entrega** (entrada → banco → modelo → saída, entregável 6 do enunciado)
está em [arquitetura.md § Diagrama final](arquitetura.md#diagrama-final-entrada--banco--modelo--saída),
em Mermaid, com a regra de leitura e a lista do que **não** aparece nele de propósito. Este guia
não redesenha o diagrama: ele tem uma fonte só.

Duas leituras complementares:

- **Contrato entre a API e o dispositivo** (tópicos, payloads, QoS, retained):
  [contrato-mqtt.md](contrato-mqtt.md). Mudou lá, mudam o firmware e a API juntos.
- **Organização interna da API** (routes → services → clients/repositories → db), módulo a
  módulo: [arquitetura.md § Organização interna da API](arquitetura.md#organização-interna-da-api).

## 3. O que está implementado

> **Esta tabela é de conteúdo, não de status.** O status oficial de cada feature — pronta, em
> revisão, bloqueada ou fora do escopo — está em [`feature/README.md`](../feature/README.md), e é
> ele que vale. Aqui a pergunta é outra: *o que essa feature faz, onde está o código e como eu vejo
> funcionando?*
>
> Duas features aparecem abaixo com ressalva porque a ressalva é parte da verdade: **W10** (alerta
> por Telegram) foi **decidida fora do escopo** e não existe; as oito features do firmware
> (**E1–E8**) estão implementadas e compilam, mas **não há captura da simulação no Wokwi**.

### 3.1 Infraestrutura (I)

| ID | O que faz | Código | Como ver funcionando |
|---|---|---|---|
| I1 | Cliente único da Open-Meteo (elevação, previsão, histórico) com cache por TTL, *stale-if-error* e conversão de falha em 503 | `api/app/clients/open_meteo.py`, `app/core/cache.py`, `app/services/weather.py` | Qualquer rota de `farms`; com a Open-Meteo fora, a resposta vira 503 com mensagem em português |
| I2 | Ponte MQTT: assina telemetria, eventos e status, valida cada payload contra o contrato, deduplica eventos e publica `config` retained | `api/app/mqtt/bridge.py`, `handlers.py`, `publisher.py`, `app/schemas/mqtt.py` | Suba a API e observe o log; ou `mosquitto_sub -h broker.hivemq.com -t 'agrishield/fiap-sompo-2026/#' -v` |
| I3 | Persistência em SQLite: telemetria, eventos, status e configs publicados, com retenção de 7 dias para a telemetria | `api/app/models.py`, `app/db.py`, `app/repositories/devices.py` | `GET /api/v1/devices/{id}/telemetry?minutes=10` depois de rodar o simulador |
| I4 | Ambiente de demo: um comando sobe API + front, confere as duas chaves, espera o `/health`, aquece o cache e derruba tudo com um Ctrl+C | `scripts/run-demo.sh` | `./scripts/run-demo.sh --conferir` (só confere) e `--aquecer` (sobe tudo) |
| I5 | Segurança e rastreabilidade: `X-API-Key` nas escritas, log estruturado com `request_id`, trilha de decisões e hash SHA-256 do payload cru | `api/app/core/security.py`, `logging.py`, `versions.py`, `app/repositories/audit.py` | `GET /api/v1/audit?limit=5` **com** o cabeçalho `X-API-Key` (sem ele: 401) |
| I6 | Simulador de dispositivo no mesmo contrato do firmware + testes ponta a ponta com broker real | `scripts/simulate_device.py`, `api/tests/e2e/` | `cd api && uv run pytest -m e2e -s` |
| I7 | Execução em Docker: API, front **e broker MQTT** em containers, banco em volume. O ESP32 fica fora (é simulado) e consome o broker pelo IP da LAN | `docker-compose.yml`, `docker/`, `.dockerignore` | `cp docker/.env.example .env && docker compose up --build` |

### 3.2 Dados e modelo (D)

| ID | O que faz | Código | Como ver funcionando |
|---|---|---|---|
| D1 | Ingestão das apólices reais do PSR/SISSER para a tabela `policy`, com relatório de qualidade e **descarte de qualquer coluna pessoal na leitura** | `api/app/services/psr_ingest.py`, `scripts/download_psr.py`, `load_psr.py`, `build_psr_sample.py` | `uv run --project api python scripts/load_psr.py --sample` (usa a amostra versionada) |
| D2 | Dataset de treino: uma linha por apólice cruzando relevo (W2) e clima da vigência (I1), com recorte que impede vazamento temporal; execução retomável | `api/app/services/dataset.py`, `scripts/build_dataset.py` | `data/dataset_treino.parquet` + a ficha `data/dataset_treino.json` (tamanho, semente, chamadas gastas) |
| D3 | Modelo treinado, versionado e comparado com o **baseline por regras** na mesma tabela; a API carrega o artefato, nunca treina | `api/app/services/model.py`, `scripts/train_model.py`, `api/app/data/model/` | `uv run --project api python scripts/train_model.py`; métricas atuais em [dados-e-modelo.md](dados-e-modelo.md#resultados-do-modelo-d3) |

### 3.3 Plataforma — API + front-web (W)

| ID | O que faz | Código (API · front) | Como ver funcionando |
|---|---|---|---|
| W1 | Catálogo das fazendas de demonstração, validado no boot (a API não sobe com catálogo inválido) | `app/data/farms.json`, `services/farms.py` · `components/farm_picker.py` | `GET /api/v1/farms` · seletor na barra lateral |
| W2 | Mapa de relevo: grade 10 × 10 com inclinação, orientação e classe de terreno, cache de 24 h | `services/terrain.py` · `views/risk_map.py`, `components/cell_map.py` | `GET /api/v1/farms/{id}/terrain` · *Mapa de risco → Relevo* |
| W3 | Previsão de risco em 7 dias: estado do solo, limite do dia e perigo por célula, cada alerta com o motivo em números | `services/risk.py`, `scenarios.py` · `views/risk_map.py` | `GET /api/v1/farms/{id}/risk?days=7` · *Mapa de risco → Previsão de risco* |
| W4 | Limite de inclinação do dia por equipamento e publicação retained no MQTT (no boot, de hora em hora e pelo botão) | `services/limits.py`, `mqtt/publisher.py` · `views/equipment.py` | `GET /api/v1/devices/{id}/limit` · botão **Enviar ao equipamento** |
| W5 | Painel do equipamento ao vivo: status online/offline, série de 10 min, eventos e alerta de capotamento | `services/devices.py`, `routes/devices.py` · `views/equipment.py` | `GET /api/v1/devices/{id}/status` · *Equipamento ao vivo* |
| W6 | Recomendações e janelas seguras do dia, em frases com números, sempre lembrando que a janela **não** libera a área vermelha | `services/recommendations.py` · `views/risk_map.py` | `GET /api/v1/farms/{id}/recommendations` · card **O que fazer** |
| W7 | Perigos extras por célula: raio, vento e incêndio (regra dos 30), somados ao capotamento e ao atolamento | `services/risk.py` (lista `HAZARDS`) · `views/risk_map.py` | filtro **Perigos** na aba *Previsão de risco* |
| W8 | Perfil de subscrição do terreno: score 0–100 e classe A/B/C, função pura sobre o relevo | `services/underwriting.py` · `views/underwriting.py` | `GET /api/v1/farms/{id}/underwriting` · tela *Subscrição* |
| W9 | Replay de acidentes reais noticiados: o mesmo motor na data e no ponto do acidente, com as limitações na resposta | `services/replay.py`, `app/data/replay_cases.json` · `views/replay.py` | `POST /api/v1/replay` · tela *Replay de acidentes* |
| W10 | **Não existe.** Alerta por Telegram — decidido **fora do escopo** (exige token de bot, credencial de terceiro e canal a manter) | — | — |
| W11 | Histórico do equipamento (prévia do Passaporte Digital): acumulado do período e linha do tempo, com a própria API declarando o que ainda não é | `services/history.py` · `views/equipment.py` | `GET /api/v1/devices/{id}/history?days=7` · seção **Passaporte (prévia)** |
| W12 | Relatórios e tendências por **equipamento, região e cultura**, cada um com o `purpose` e exportação em CSV pronta para o Excel em pt-BR | `services/reports.py`, `routes/reports.py` · `views/reports.py` | `GET /api/v1/reports/region?state=MG` · tela *Relatórios* |
| W13 | Score híbrido: a probabilidade do modelo ao lado do nível por regras, com a ressalva montada a partir do artefato — o modelo **não** altera nível, limite nem motivo | `services/model_scoring.py` · `views/risk_map.py` | cartão **Probabilidade de sinistro (modelo)** na aba *Previsão de risco* |
| W14 | Cadastro de maquinário e vínculo do ESP32: a única escrita de usuário do sistema, com chave de API e trilha de auditoria. O limite do cadastro é **informativo** e não altera o que vai para a máquina | `services/machines.py`, `repositories/machines.py`, `routes/machines.py` · `views/machines.py` | tela *Maquinário*: cadastre e vincule `tractor-01` |

A lista completa das rotas, com método e feature de origem, está em
[arquitetura.md § Endpoints da API (v1)](arquitetura.md#endpoints-da-api-v1) e em
[`api/README.md`](../api/README.md#endpoints) — e a fonte viva é sempre `/docs` com a API no ar.

### 3.4 Dispositivo — ESP32 no Wokwi (E)

Arquivo único: [`iot/src/main.ino`](../iot/src/main.ino). Circuito e pinagem em
[`iot/README.md § Circuito`](../iot/README.md#circuito).

| ID | O que faz | Como ver funcionando |
|---|---|---|
| E1 | Inclinômetro: MPU6050 a 10 Hz com média móvel; a grandeza comparada com o limite é `max(\|roll\|, \|pitch\|)` | Wokwi: clique no MPU6050 e ajuste a aceleração ([tabela de ângulos](../iot/README.md#simulando-inclinação)) |
| E2 | Alerta local: três níveis com um LED por vez, histerese, buzzer, e evento `tilt_alert` ao entrar no vermelho | Wokwi: suba a inclinação acima do limite e olhe LEDs, buzzer e Serial |
| E3 | Recebe o limite do dia pelo `config` retained, valida a faixa, guarda na NVS e recalcula o nível na hora | publique um `config` com `mosquitto_pub -r` ([exemplo](../iot/README.md#recebendo-o-limite-do-dia-e3)) |
| E4 | Telemetria a cada 5 s (e na mudança de nível), com `ts` do NTP e contador de sequência | `mosquitto_sub` no prefixo do projeto, ou o painel ao vivo do front |
| E5 | Detecção de capotamento por inclinação sustentada **ou** impacto, com estado travado e os 30 s anteriores no evento | Wokwi: 60° por 3 s ([como reproduzir](../iot/README.md#simulando-capotamento-e5)) |
| E6 | Microclima com DHT22 e a **regra dos 30** (temperatura, umidade, vento) publicada na telemetria | Wokwi: ajuste o DHT22 e publique `wind_max_kmh` no `config` |
| E7 | Display OLED com inclinação, limite, estado do solo e nível, redesenhado só quando muda | Wokwi: a tela do SSD1306 |
| E8 | Botão de ocorrência: um toque publica `incident_report` com os mesmos 30 s de contexto e confirma com bipes | Wokwi: clique no botão do pino 33 |

**Pendência conhecida:** o firmware compila (`pio run`) e os ângulos de E1 foram conferidos no
Wokwi em 25/09 ([evidência](evidencias/2026-09-25-inclinometro-wokwi.md), com erro ≤ 0,5°). Falta a
captura que comprova **LEDs, buzzer, display, botão e o evento de capotamento chegando ao broker** —
é a tarefa T6 do time e o motivo de E2–E8 continuarem "em revisão" em
[`feature/README.md`](../feature/README.md).

## 4. Onde há inteligência artificial no projeto

Esta seção existe porque a pergunta "onde está a IA?" tem três respostas neste projeto, e elas
valem coisas muito diferentes. Misturá-las seria vender o que não temos.

| Camada | O que é | Aprende com dados? | Decide algo para o operador? |
|---|---|---|---|
| **Motor de regras** (W3) | Limiares de chuva, vento, inclinação e estado do solo, calibrados à mão | ❌ | ✅ **Sim — é ele que manda** |
| **Modelo preditivo** (D3) | Regressão logística treinada em 2.256 apólices reais do PSR | ✅ | ❌ Só informa um card na tela |
| **Experimento MLP** (25/09) | Rede neural pequena, desligada por padrão | ✅ | ❌ Nada. Só aparece se você ligar |

**O alerta que chega ao trator vem das regras, não de aprendizado de máquina.** Essa é a frase
importante, e ela é uma escolha, não uma limitação escondida: o rótulo que temos é *"houve
indenização agrícola nesta apólice"*, que não é *"a máquina capotou"*. Um modelo treinado nesse
rótulo aprende exposição climática de lavoura — seca e geada incluídas —, não acidente de máquina.
Deixá-lo comandar o limite de inclinação seria usar a evidência errada para a decisão errada.

### O que é a MLP, em uma frase

**MLP** (*Multi-Layer Perceptron*) é o tipo mais simples de rede neural: entradas, uma camada
intermediária de neurônios e uma saída. A nossa tem **8 neurônios em uma única camada** — pequena de
propósito, porque com 2.256 linhas e ~200 casos positivos uma rede grande decoraria os dados em vez
de aprender.

### O que ela mudou no projeto: quase nada, e isso é intencional

No conjunto de teste (2024) ela marcou **AUC-PR 0,150**, contra 0,144 da regressão logística e
0,074 do baseline por regras. Ou seja: ficou **empatada com a regressão logística**, e a diferença
entre as duas está dentro do ruído de um teste com **26 casos positivos** — abaixo dos 30 que o
projeto definiu como mínimo para afirmar qualquer coisa.

Por isso ela entrou como **experimento isolado**, e o isolamento é verificável no código:

- artefato próprio (`api/app/data/model/risk_neural_model_v1.joblib`), separado do modelo oficial;
- só é treinada com `--somente-rede-opcional` ou `--incluir-rede-opcional`;
- a API só a pontua se você pedir `?include_experimental_mlp=true`;
- na tela, o toggle **"Mostrar score experimental da MLP"** começa **desligado**;
- ela **não** entra em nível de risco, limite de inclinação, recomendação, motivo ou alerta.

**Como ela afeta o projeto, então?** Ela responde à pergunta "vocês tentaram rede neural?" com um
número medido em vez de um palpite — e a resposta honesta é *"tentamos, empatou, e por isso não
está no caminho da decisão"*. Um experimento negativo documentado vale mais que um modelo bonito
usado onde não devia.

Método, métricas completas e ressalvas estatísticas: [dados-e-modelo.md](dados-e-modelo.md).

## 5. Como foi implementado: as decisões que explicam o código

Sete decisões respondem pela maior parte do que parece estranho no código. Cada uma tem o ADR
correspondente em [decisoes.md](decisoes.md).

**1. Regras explicáveis decidem o alerta; o modelo entra ao lado** (ADR-006, revisada pela
ADR-010). O operador precisa saber *por quê* — "inclinação de 13° acima do limite de 10°, solo
encharcado" é discutível; uma probabilidade não é. Além disso, a regra roda offline no próprio
ESP32. O modelo dá a segunda leitura para a seguradora, e a comparação honesta com o baseline
está em [dados-e-modelo.md](dados-e-modelo.md#resultados-do-modelo-d3) e em
[regras-de-risco.md § 11](regras-de-risco.md).

**2. Cache com *stale-if-error*** (I1). A Open-Meteo é gratuita e tem cota; durante a demo ela
pode recusar. Quando a chamada falha e existe resposta vencida no cache, a resposta vencida é
reaproveitada com aviso no log; sem nada no cache, a API responde **503 em português** em vez de
mostrar um erro cru. É a diferença entre um mapa velho e uma tela quebrada na apresentação.

**3. MQTT com `config` retained e deduplicação de eventos** (ADR-003, ADR-008, I2). O ESP32 roda
na nuvem do Wokwi e não enxerga o `localhost` do notebook: com MQTT os dois lados só fazem
conexões **de saída**. O `config` é **retained** para o dispositivo receber o último limite assim
que conecta, sem esperar o próximo ciclo. E como o firmware publica cada evento três vezes (a
biblioteca só faz QoS 0), a ponte deduplica por `event_id` **e** a tabela tem `UNIQUE` — duas
travas, porque a memória da ponte se perde num reinício.

**4. SQLite sem Alembic** (ADR-009). Os dados são de demo e o esquema é criado no boot. Mudou o
esquema, apaga-se o `.db`. A consequência aparece no código: a integridade dos eventos ficou em
**tabela própria** (`event_integrity`) em vez de virar coluna de `device_event`, porque
acrescentar coluna exigiria derrubar o banco — levando junto a carga do PSR, que leva minutos
para refazer.

**5. Segurança que falha fechada** (ADR-013, I5). Chave no cabeçalho `X-API-Key` nas rotas que
escrevem ou publicam, comparada em tempo constante. **Sem chave configurada, nada passa** —
esquecer a variável de ambiente não pode virar porta aberta. O 401 tem a mesma mensagem para
chave ausente, inválida e servidor sem chave, para não contar ao atacante em que pé está a
configuração. Nenhum cabeçalho, corpo ou *query string* entra no log, por construção.

**6. Toda decisão vira registro** (I5). Score de risco, limite publicado e alerta do equipamento
gravam uma linha em `decision_log` com entrada, saída, versão da regra e versão do modelo. A
versão da regra é conferida **por teste** contra o título de [regras-de-risco.md](regras-de-risco.md):
documento e código não podem divergir em silêncio. A versão do modelo viaja com a decisão, lida do
artefato, porque muda a cada retreino.

**7. Dado real do PSR, sem nenhum dado pessoal** (ADR-011). O CSV público traz nome e documento do
segurado; a leitura passa uma **lista branca de colunas** ao pandas, então esses campos não chegam
nem a virar `DataFrame`, e há teste que falha se qualquer valor pessoal aparecer no banco. O
resíduo que sobra — o `proposal_id`, guardado para tornar a carga idempotente — está declarado com
todas as letras em [`api/README.md § Resíduo de dado pessoal`](../api/README.md#resíduo-de-dado-pessoal-lgpd),
inclusive o caminho para eliminá-lo.

Decisões menores, mas que aparecem no dia a dia: **uv e pip suportados ao mesmo tempo** (ADR-007,
os `requirements*.txt` são gerados e a CI falha se divergirem do lock) e **Open-Meteo como fonte
única** de clima e relevo (ADR-005), em vez de INMET + ANA + SRTM + IBGE.

## 6. Como executar tudo, do zero

> **Atalho, se você só quer ver funcionando:** `cp docker/.env.example .env && docker compose up
> --build` sobe a API e o front em containers, sem instalar Python nem dependências. O ESP32 fica
> fora (é simulado no navegador). Ver [docker/README.md](../docker/README.md). O resto desta seção
> é o caminho nativo, que é o da apresentação — o `run-demo.sh` aquece o cache da Open-Meteo.

### 6.1 Pré-requisitos

| Ferramenta | Para quê |
|---|---|
| Python 3.11+ e **[uv](https://docs.astral.sh/uv/)** (recomendado) ou pip | `api/` e `front-web/` |
| VS Code + extensões **PlatformIO IDE** e **Wokwi Simulator**, ou uma conta em [wokwi.com](https://wokwi.com) | firmware |
| `mosquitto-clients` (opcional) | acompanhar o MQTT pelo terminal |

Instalação passo a passo e solução de problemas:
[ambiente-de-desenvolvimento.md](ambiente-de-desenvolvimento.md).

### 6.2 A demo inteira, em um comando (Linux e macOS)

```bash
cp api/.env.example api/.env                 # escolha uma chave em AGRISHIELD_API_KEYS
cp front-web/.env.example front-web/.env     # AGRISHIELD_API_KEY = uma das chaves acima
./scripts/run-demo.sh --aquecer              # sobe API + front, confere /health e aquece o cache
```

Outras opções: `--conferir` (só confere o ambiente e sai), `--sem-front` (só a API),
`--porta-api` / `--porta-front`, `--ajuda`. O script confere que as **duas** chaves combinam — é o
que faz o botão "Enviar ao equipamento" responder 401 no meio da apresentação — e um Ctrl+C derruba
os dois processos. Detalhes em [`scripts/readme.md`](../scripts/readme.md#subir-a-demo-run-demosh).

**Windows:** o script é bash. Use o WSL ou os dois terminais de PowerShell descritos no
[README da raiz](../README.md#sem-docker).

### 6.3 Cada parte isolada

```bash
# API — http://localhost:8000/docs
cd api && uv sync && uv run fastapi dev app/main.py

# Front-web — http://localhost:8501 (precisa da API no ar)
cd front-web && uv sync && uv run streamlit run app.py
```

Com pip, em qualquer um dos dois: `python -m venv .venv && source .venv/bin/activate &&
pip install -r requirements-dev.txt`, e depois `uvicorn app.main:app --reload` ou
`streamlit run app.py`.

Variáveis do front: `AGRISHIELD_API_URL` (padrão `http://localhost:8000`) e `AGRISHIELD_API_KEY`
(só o botão de envio do limite usa). Variável exportada no terminal **vence** o `.env`.

### 6.4 O dispositivo no Wokwi

- **VS Code:** abra `iot/`, compile com `pio run`, depois `F1` → *Wokwi: Start Simulator*.
- **Navegador:** crie um projeto ESP32 em wokwi.com e cole `iot/src/main.ino`, `iot/diagram.json`
  e `iot/libraries.txt`. O Serial deve mostrar `[wifi] conectado` e `[mqtt] conectado`.

Passo a passo, tabela de ângulos e como reproduzir capotamento, regra dos 30 e botão de ocorrência:
[`iot/README.md`](../iot/README.md).

### 6.5 A base real do PSR, o dataset e o modelo

Opcional para rodar a API; necessário para refazer o dataset e o modelo. Os CSVs completos **não**
estão no Git. Rode **a partir da raiz**, com o ambiente da API:

```bash
uv run --project api python scripts/download_psr.py       # baixa os CSVs para data/raw/
uv run --project api python scripts/load_psr.py           # carrega no SQLite + relatório de qualidade
uv run --project api python scripts/load_psr.py --sample  # só a amostra versionada (rápido, offline)
uv run --project api python scripts/build_dataset.py      # gera data/dataset_treino.parquet (D2)
uv run --project api python scripts/train_model.py        # treina, compara com o baseline e salva o artefato
```

Opções úteis: `build_dataset.py` aceita `-n/--amostra`, `--seed`, `--rpm`, `--reiniciar` e
`--saida` (é **retomável**: pode ser interrompido e continuado); `train_model.py` aceita
`--dataset`, `--alvo`, `--seed` e `--nao-salvar`. Tamanho da carga, tempo e licença dos dados em
[dados-e-modelo.md](dados-e-modelo.md) e [`data/README.md`](../data/README.md).

> ⚠️ **A cota da Open-Meteo é por peso, não por ritmo.** Uma requisição que cobre mais de duas
> semanas conta como várias — e a janela do dataset é a vigência da apólice. Por isso
> `build_dataset.py` esgota a cota **diária** enquanto o mapa da demo continua funcionando. A cota
> vira às 00:00 UTC. A conta está em
> [dados-e-modelo.md § Orçamento de chamadas](dados-e-modelo.md#orçamento-de-chamadas-da-open-meteo).

### 6.6 Testes, qualidade e medições

```bash
# unitários, sem rede (Open-Meteo e MQTT mockados)
cd api        && uv run ruff check . && uv run ruff format --check . && uv run pytest
cd front-web  && uv run ruff check . && uv run ruff format --check . && uv run pytest
cd iot        && pio run

# ponta a ponta: API de verdade + broker público + simulador (~2 min, precisa de internet)
cd api && uv run pytest -m e2e -s

# simulador sozinho (cenários: normal, alerta, capotamento, sujo, rajada, queda)
uv run --project api python scripts/simulate_device.py --scenario rajada --count 100

# desempenho do mapa (critério 7 da US-03): mede a rota fria e com cache
uv run --project api python scripts/medir_mapa.py
uv run --project api python scripts/medir_mapa.py --sem-clima   # afere só o mecanismo
```

`medir_mapa.py` **recusa rodar** com a cota da Open-Meteo esgotada, de propósito: nesse estado ele
mediria a recusa, não o mapa.

Mudou dependência Python (`uv add`)? Rode `./scripts/sync-requirements.sh` — a CI falha se os
`requirements*.txt` divergirem do lock.

## 7. Como verificar que funciona

Três níveis, com propósitos diferentes:

| Nível | Comando | O que cobre |
|---|---|---|
| **Unitário / de rota** | `uv run pytest` em `api/` e em `front-web/` | Regras puras (relevo, risco, limite, recomendações, subscrição, relatórios, modelo), rotas, validação de payload MQTT, segurança, auditoria e cada página do front com a API mockada. **Sem rede**: as respostas da Open-Meteo são fixtures reais capturadas do serviço |
| **Ponta a ponta (I6)** | `cd api && uv run pytest -m e2e -s` | API de verdade + `broker.hivemq.com` + simulador: telemetria campo a campo, rajada (perda e duplicidade), payloads inválidos, capotamento (dedup + contexto + auditoria), queda do dispositivo e do broker, `config` chegando ao equipamento e os tempos do painel. Fica **fora da CI** por usar rede |
| **Medição** | `scripts/medir_mapa.py` | Tempo do mapa a frio e com cache (critério 7 da US-03) |

**Onde estão as evidências:** [`document/evidencias/`](evidencias/README.md). Cada relatório traz
o comando executado, a **saída real** e o veredito; as saídas completas ficam em
`evidencias/logs/`. Hoje há relatórios da integração ponta a ponta, do ambiente de demo, da
retomada do dataset e do comportamento do sistema com a Open-Meteo realmente fora do ar.

**A rastreabilidade história → feature → arquivo → evidência** está na matriz de
[user-stories.md § Matriz de rastreabilidade](user-stories.md#matriz-de-rastreabilidade), com as
dez histórias dos quatro perfis (operador, gestor de frota, técnico de manutenção e analista da
seguradora).

**O que ainda não tem evidência** está declarado, não escondido: captura do Wokwi (T6), prints das
telas ([lista do que capturar](evidencias/prints/README.md)) e a medição de desempenho do mapa.

## 8. Limitações declaradas

Escritas aqui para não dependerem da boa vontade de quem apresenta:

- **Não há hardware real.** O ESP32 roda simulado no Wokwi, com o slider do MPU6050 no lugar da
  inclinação real da máquina. Não há GPS, então o limite enviado vale para a fazenda inteira, não
  para a célula onde a máquina está.
- **O rótulo do modelo é de seguro agrícola, não de máquina.** A base pública do PSR registra
  perda de lavoura; o perigo que o alerta trata é capotamento e atolamento de máquina. É uma
  aproximação, e ela precisa ser dita em toda apresentação. A comparação com o baseline, o
  intervalo de confiança e a auditoria do resultado estão em
  [dados-e-modelo.md](dados-e-modelo.md#resultados-do-modelo-d3).
- **Os limiares da v1 não têm fonte publicada.** São valores iniciais escolhidos pelo time, ainda
  não calibrados com dados de sinistro — e é justamente por isso que o score é explicável: dá para
  discordar do número sem ter de confiar numa caixa-preta. A tabela a preencher está em
  [regras-de-risco.md § Fontes dos limiares (T1)](regras-de-risco.md#fontes-dos-limiares-t1).
- **Os pesos do score de subscrição são v1 e arbitrários**, e a própria resposta da API diz isso
  ao subscritor (`calibration_note`).
- **O DEM de 90 m suaviza encostas curtas** e a previsão é de um ponto só (o centro da fazenda):
  chuva localizada pode escapar. Ver
  [regras-de-risco.md § Limitações conhecidas](regras-de-risco.md#limitações-conhecidas-declarar-no-pitch).
- **As fazendas são de demonstração**, com recortes escolhidos pelo time; não há integração com
  CAR nem com a carteira real da Sompo.
- **O Passaporte Digital aparece só como prévia** (W11), e a própria API declara o que ele ainda
  não é.
- **O replay tem cinco casos** — não é amostra, e o placar não é taxa de acerto do produto. A
  própria resposta da API diz isso junto do número.
- **Pendências que não são de código:** captura do Wokwi, prints das telas, gravação do vídeo e
  ensaio da demo. Situação atualizada em [entregaveis.md](entregaveis.md).

## 9. Mapa de documentos

Qual arquivo é a **fonte da verdade** de cada assunto — é nele que se corrige, e são os outros que
apontam para ele:

| Assunto | Fonte da verdade |
|---|---|
| Visão geral, execução e evolução das sprints | [`README.md`](../README.md) da raiz |
| Panorama completo (este guia) | `document/guia-do-projeto.md` |
| Componentes, fluxos e **diagrama final** da entrega | [arquitetura.md](arquitetura.md) |
| Fórmulas, limiares e escala de níveis do risco | [regras-de-risco.md](regras-de-risco.md) |
| Tópicos e payloads entre API e ESP32 | [contrato-mqtt.md](contrato-mqtt.md) |
| Fontes de dados, pipeline, features e **métricas do modelo** | [dados-e-modelo.md](dados-e-modelo.md) |
| Status de cada feature e cronograma | [`feature/README.md`](../feature/README.md) |
| Histórias por perfil e **rastreabilidade** | [user-stories.md](user-stories.md) |
| Checklist dos 9 entregáveis do enunciado | [entregaveis.md](entregaveis.md) |
| Decisões de arquitetura e de escopo (ADRs) | [decisoes.md](decisoes.md) |
| Detalhe de implementação da API | [`api/README.md`](../api/README.md) |
| Detalhe das telas | [`front-web/README.md`](../front-web/README.md) |
| Pinagem, simulação e comportamento do firmware | [`iot/README.md`](../iot/README.md) |
| Scripts auxiliares, simulador e medições | [`scripts/readme.md`](../scripts/readme.md) |
| Instalação e solução de problemas | [ambiente-de-desenvolvimento.md](ambiente-de-desenvolvimento.md) |
| Roteiro da apresentação ao vivo | [demo.md](demo.md) |
| Roteiro do vídeo de entrega | [roteiro-video.md](roteiro-video.md) |
| Relatórios de validação e prints | [evidencias/](evidencias/README.md) |
| Convenções de código, git e definição de pronto | [padroes-de-codigo.md](padroes-de-codigo.md) · [fluxo-git.md](fluxo-git.md) · [definicao-de-pronto.md](definicao-de-pronto.md) |
