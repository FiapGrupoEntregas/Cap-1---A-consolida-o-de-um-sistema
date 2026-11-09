# Fase 4 — Dashboard com Data Science

Pasta: [`fase4/`](../../fase4/) · Vídeo da entrega original: <https://youtu.be/QSCSz7Z3c8s>

## O que faz

Um ESP32 no Wokwi lê sensores de solo a cada 5 segundos e envia as leituras para uma **API
FastAPI**, que grava no Oracle (tabela `SOIL_DATA`). Uma **dashboard Streamlit** busca os dados
pela API, treina um modelo de regressão e prevê o próximo ciclo. **É esta dashboard que a Fase 7
evolui para disparar os outros serviços.**

```
ESP32 (Wokwi) --HTTP POST /soil--> API FastAPI --> Oracle SOIL_DATA
                                        ^
Dashboard Streamlit --GET /soil/month---+
```

## Sensores do ESP32 (`iot/`)

| Sensor | Pino | Campo enviado |
|---|---|---|
| DHT22 | GPIO 15 | `air_humidity`, `air_temperature` |
| Potenciômetro (umidade do solo) | GPIO 32 | `soil_moisture_raw`, `soil_moisture_percent` |
| Potenciômetro (pH) | GPIO 33 | `ph` |
| Potenciômetros (N, P, K) | GPIO 35, 25, 26 | `nitrogen`, `phosphorus`, `potassium` (níveis numéricos) |
| LDR | GPIO 34 | `light_raw`, `light_percent` |

O firmware conecta na rede `Wokwi-GUEST` e envia para `http://host.wokwi.internal:8000/soil`.

## API (`src/api.py`)

| Método e rota | O que faz |
|---|---|
| `POST /soil` | Grava uma leitura (latitude e longitude opcionais) |
| `GET /soil?limit=&offset=` | Lista as leituras, da mais recente para a mais antiga |
| `GET /soil/{id}` | Uma leitura |
| `GET /soil/month/{ano}/{mes}` | Leituras de um mês |
| `POST /simulate` | Insere 200 leituras simuladas e correlacionadas |

Documentação interativa em <http://localhost:8000/docs>.

## Machine Learning (`src/core/ml_pipeline.py`)

- Modelo: **Random Forest** (`RandomForestRegressor`, 100 árvores).
- Alvos que podem ser previstos: umidade do solo, pH, N, P, K, temperatura e umidade do ar,
  luminosidade.
- Métricas exibidas: MAE, MSE, RMSE e R².
- O notebook `farmtech_fase4.ipynb` registra a análise feita na entrega original.

## Como executar

As credenciais do Oracle vêm do `.env` único da raiz (ver [`.env.example`](../../.env.example)).

```bash
cd fase4/src
uv run python scripts/create_table.py          # cria a tabela SOIL_DATA (uma vez)
uv run uvicorn api:app --port 8000             # API
uv run streamlit run app.py                    # dashboard (em outro terminal)
```

Para o ESP32: abrir `fase4/iot/` no VS Code com as extensões PlatformIO e Wokwi e iniciar a
simulação com a API no ar.
