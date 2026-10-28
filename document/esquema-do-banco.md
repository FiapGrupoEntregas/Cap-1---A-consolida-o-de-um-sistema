# Estrutura do banco de dados

> **Fonte da verdade:** [`api/app/models.py`](../api/app/models.py). Este documento descreve o que
> está lá, com o porquê de cada escolha — o código define, aqui se explica.
>
> Extraído do banco em execução em **28/09/2026** (`PRAGMA table_info` e `index_list`), não da
> memória. Para reconferir: `docker compose exec api python -c "..."` ou `sqlite3 agrishield.db
> .schema`.

**SQLite, oito tabelas, sem migrações.** O banco nasce no `lifespan` da API, por `create_db()`
([ADR-009](decisoes.md)). Mudou o esquema, apague o `.db` local — é uma decisão de prazo, e a
consequência está declarada no [backlog](backlog-pos-entrega.md), item 14.

## Visão geral

| Tabela | O que guarda | Quem escreve | Origem |
|---|---|---|---|
| [`policy`](#policy) | Apólices e sinistros reais do seguro rural | `scripts/load_psr.py` | D1 |
| [`telemetry`](#telemetry) | Leituras do ESP32, uma a cada 5 s | ponte MQTT | I3, E4 |
| [`device_event`](#device_event) | Eventos do dispositivo, com o payload cru | ponte MQTT | I3, E5, E8 |
| [`device_status`](#device_status) | Estado atual de cada equipamento | ponte MQTT | I3, W5 |
| [`published_config`](#published_config) | Todo limite que a API publicou | publicador MQTT | W4, I5 |
| [`machine`](#machine) | Cadastro da frota e o vínculo com o ESP32 | API (com chave) | W14 |
| [`decision_log`](#decision_log) | Toda decisão do sistema, com entrada e saída | API | I5 |
| [`event_integrity`](#event_integrity) | Hash SHA-256 do payload cru de cada evento | ponte MQTT | I5 |

Duas convenções valem para o banco inteiro:

- **Tudo em UTC sem fuso.** O SQLite não guarda fuso, então gravar "com fuso" seria mentira. `ts` é
  a hora do **dispositivo** (epoch do NTP) e `received_at` é a hora da **API** — a diferença entre
  as duas é informação, não ruído.
- **Nenhum dado pessoal**, em nenhuma tabela ([ADR-011](decisoes.md)). Ver a ressalva do
  `proposal_id` abaixo.

---

## `policy`

**1.525.473 linhas.** As apólices do PSR/SISSER (Ministério da Agricultura, dados abertos CC-BY,
2006–2025). É a base do modelo preditivo (D3) e dos relatórios por região e cultura (W12).

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | INTEGER | PK |
| `proposal_id` | VARCHAR | **UNIQUE** — deduplicação entre cargas |
| `insurer` · `municipality` · `state` · `geocode_ibge` | VARCHAR | `state` com 2 caracteres |
| `lat` · `lon` | FLOAT | **NOT NULL** — sem coordenada a linha não serve ao dataset |
| `coordinate_source` | VARCHAR | **NOT NULL** — diz se a coordenada é da lavoura ou do município |
| `crop` · `area_ha` · `coverage_value` · `premium` | | a carteira |
| `start_date` · `end_date` · `policy_year` | | vigência, que define o recorte temporal do treino |
| `indemnity_value` | FLOAT | nulo = sem indenização; é o que vira o rótulo |
| `event_category` | VARCHAR | **NOT NULL** — causa normalizada (seca, granizo, geada, …) |
| `created_at` | DATETIME | quando a linha entrou no banco |

**Índices:** `proposal_id` (único), `(state, policy_year)`, `(lat, lon)`, `event_category` — os três
últimos são os recortes que os relatórios e o gerador de dataset realmente fazem.

> ⚠️ **LGPD.** O CSV público do PSR traz **nome e documento do produtor**, e as duas colunas são
> **descartadas na leitura** — nunca chegam ao banco, com teste que falha se algo escapar. O
> `proposal_id` **permanece**, porque sem ele não há deduplicação nem reprodutibilidade; ele permite
> vínculo com o CSV público, que contém o nome, e essa limitação está declarada na
> [I5](../feature/I5-seguranca-rastreabilidade.md).

---

## `telemetry`

Uma leitura a cada 5 s por equipamento (E4). É o que alimenta o painel ao vivo (W5), o histórico
(W11) e o relatório por equipamento (W12).

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | INTEGER | PK |
| `device_id` | VARCHAR | **NOT NULL** |
| `ts` | DATETIME | hora do **dispositivo** (NTP) |
| `received_at` | DATETIME | hora da **API** |
| `seq` | INTEGER | sequência do dispositivo; reinicia no boot |
| `roll_deg` · `pitch_deg` · `accel_g` | FLOAT | **NOT NULL** — a medida do MPU6050 |
| `temp_c` · `humidity_pct` | FLOAT | **nulos quando o DHT22 falha** — o contrato pede `null`, não `0` |
| `fire_conditions` | INTEGER | quantas das três condições da regra dos 30 estão ativas |
| `tilt_limit_deg` | FLOAT | **NOT NULL** — o limite que o dispositivo estava aplicando |
| `alert_level` | VARCHAR | **NOT NULL** — `green`, `yellow`, `red` ou `rollover` |

**Índices:** `(device_id, received_at)` e `device_id`.

**Retenção: 7 dias.** A telemetria mais velha é apagada quando a API sobe (`purge_old_telemetry`).
É volume alto e valor baixo depois de uma semana — diferente dos eventos, que ficam.

> Guardar `tilt_limit_deg` **junto da leitura** é deliberado: sem isso, um retreino ou uma mudança
> de regra reescreveria o passado. A linha registra o limite que valia **naquele instante**.

---

## `device_event`

Capotamento (E5), alerta de inclinação (E2), ocorrência do operador (E8) e aplicação de limite (E3).

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | INTEGER | PK |
| `event_id` | VARCHAR | **UNIQUE** — é o que torna o reenvio idempotente |
| `device_id` · `type` | VARCHAR | **NOT NULL** |
| `ts` · `received_at` | DATETIME | do dispositivo e da API |
| `payload_json` | VARCHAR | **o payload completo**, incluindo os 30 s de contexto do capotamento |

**Índices:** `event_id` (único), `device_id`, `(device_id, received_at)`.

> O `event_id` único resolve um problema real do contrato: o firmware publica cada evento **três
> vezes** para sobreviver a perda de pacote. O banco aceita o primeiro e ignora os outros dois.
> Guardar o `payload_json` inteiro é o que permite reconstruir o evento depois sem depender de as
> colunas terem previsto tudo.

---

## `device_status`

Uma linha por equipamento. Alimentada pelo `status` retained e pelo LWT do MQTT.

| Coluna | Tipo | Nota |
|---|---|---|
| `device_id` | VARCHAR | **PK** |
| `state` | VARCHAR | **NOT NULL** — `online` ou `offline` |
| `updated_at` | DATETIME | **NOT NULL** |

> O painel cruza esta tabela com a telemetria recente: anunciar `online` sem medir nada **não** é
> estar vivo, e um `offline` do LWT derruba o equipamento mesmo com leitura recente (W5).

---

## `published_config`

Todo `config` que a API publicou para um equipamento — o registro de que o limite foi enviado.

| Coluna | Tipo |
|---|---|
| `id` | INTEGER, PK |
| `device_id` | VARCHAR, **NOT NULL** |
| `published_at` | DATETIME, **NOT NULL** |
| `payload_json` | VARCHAR, **NOT NULL** |

**Índices:** `device_id`, `(device_id, published_at)`.

---

## `machine`

Cadastro da frota (W14). É a **única tabela que o usuário escreve**, e por isso toda escrita exige
`X-API-Key` e entra no `decision_log`.

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | INTEGER | PK |
| `code` | VARCHAR(32) | **UNIQUE** — a identidade humana da máquina (ex.: `TR-001`) |
| `name` · `type` | VARCHAR | **NOT NULL** |
| `manufacturer` · `model` · `year` | | ficha do equipamento |
| `farm_id` | VARCHAR | precisa existir no catálogo (W1) |
| `device_id` | VARCHAR | **UNIQUE** — um ESP32 pertence a no máximo uma máquina |
| `base_tilt_limit_deg` | FLOAT | **informativo**: não altera o limite publicado ([ADR-014](decisoes.md)) |
| `hour_meter_h` · `acquisition_date` · `notes` | | |
| `active` | BOOLEAN | **NOT NULL** |
| `created_at` · `updated_at` | DATETIME | **NOT NULL** |

**Índices:** `code` (único), `device_id` (único), `farm_id`, `(farm_id, type)`.

> **LGPD:** os schemas de entrada usam `extra="forbid"`, então um campo como `operador` é recusado
> com 422 em vez de gravado. `notes` é texto livre e **aceita** o que for digitado — a mitigação é o
> aviso na tela, o limite de tamanho e a exclusão do campo da trilha de auditoria.

---

## `decision_log`

**Toda decisão do sistema**, com a entrada, a saída e as versões que decidiram. É o que sustenta a
explicabilidade exigida pelo enunciado (I5).

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | INTEGER | PK |
| `created_at` | DATETIME | **NOT NULL** |
| `request_id` | VARCHAR | amarra a linha ao log estruturado da requisição |
| `decision_type` | VARCHAR | **NOT NULL** — `risk`, `limit`, `underwriting`, `replay`, `machine`… |
| `entity_id` | VARCHAR | **NOT NULL** — fazenda, equipamento ou código da máquina |
| `inputs_json` · `output_json` | VARCHAR | **NOT NULL** — o que entrou e o que saiu |
| `rule_version` | VARCHAR | **NOT NULL** — versão das regras que decidiram |
| `model_version` | VARCHAR | **nulo quando nenhum modelo participou** — e isso é correto |
| `source` | VARCHAR | **NOT NULL** — quem originou (API, publicador periódico…) |

**Índices:** seis, cobrindo `(decision_type, created_at)`, `(entity_id, created_at)`, `request_id` e
`created_at` — as consultas que a trilha realmente recebe.

**Retenção:** configurável por `AGRISHIELD_DECISION_RETENTION_DAYS` (padrão 30 dias), limpa no boot.

> `model_version` nulo **não** é dado faltando: significa que aquela decisão foi tomada só por
> regras. A coluna diz *com o que aquela decisão foi tomada*, não *o que existe no projeto*.

---

## `event_integrity`

Hash do payload **cru** de cada evento MQTT, antes de qualquer interpretação.

| Coluna | Tipo | Nota |
|---|---|---|
| `event_id` | VARCHAR | **PK** |
| `device_id` | VARCHAR | **NOT NULL** |
| `payload_sha256` | VARCHAR | **NOT NULL** — hash dos bytes exatos recebidos |
| `payload_bytes` | INTEGER | **NOT NULL** — tamanho em bytes |
| `created_at` | DATETIME | **NOT NULL** |

> Serve para provar, depois, que o que está gravado é o que o equipamento publicou. Num sinistro,
> essa é a diferença entre "o sistema diz" e "dá para verificar".

---

## Como conferir o esquema por conta própria

```bash
# com a pilha em Docker
docker compose exec api python -c "
import sqlite3
c = sqlite3.connect('/data/agrishield.db')
for (n,) in c.execute(\"select name from sqlite_master where type='table'\"):
    print(n, [r[1] for r in c.execute(f'PRAGMA table_info({n})')])"

# fora do Docker
sqlite3 api/agrishield.db .schema
```

## Onde cada tabela é detalhada

| Assunto | Documento |
|---|---|
| Pipeline do PSR, features e modelo | [dados-e-modelo.md](dados-e-modelo.md) |
| Persistência, retenção e a ponte MQTT | [`api/README.md`](../api/README.md#persistência-em-sqlite-i3) |
| Trilha de auditoria e integridade | [I5](../feature/I5-seguranca-rastreabilidade.md) |
| Cadastro de maquinário | [W14](../feature/W14-cadastro-de-maquinario.md) |
| Decisão de não usar migrações | [ADR-009](decisoes.md) e [backlog](backlog-pos-entrega.md) item 14 |
