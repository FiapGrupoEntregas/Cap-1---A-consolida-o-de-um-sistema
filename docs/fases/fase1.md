# Fase 1 — Base de dados inicial (Python e R)

Pasta: [`fase1/`](../../fase1/)

## O que faz

Programa de terminal que cadastra plantios, calcula a **área** e o **insumo** de cada um e guarda
os registros em CSV. Dois scripts em R completam a fase: estatística dos registros e consulta do
clima numa API pública.

| Cultura | Formato da área | Área | Insumo |
|---|---|---|---|
| Manga | Retângulo | comprimento × largura | ruas × comprimento × litros por metro linear |
| Cana | Círculo (pivô) | π × raio² | área × kg de fertilizante por m² |

## Arquivos

| Arquivo | Papel |
|---|---|
| `src/main.py` | Entrada do programa e laço do menu (cadastrar, listar, atualizar, excluir) |
| `src/farm_math_handler.py` | Cálculo de área e insumo por cultura |
| `src/input_handler.py`, `src/menus.py` | Leitura e validação do teclado, textos do menu |
| `src/csv_handler.py` | Leitura e gravação do CSV |
| `src/model/crop.py` | Classe `Crop` (registro de plantio) |
| `src/farm_tech_solutions.csv` | Base de dados da fase (separador `;`) |
| `src/Rscripts/python-consumer.r` | Estatística (média, desvio, mediana, mínimo, máximo) por cultura a partir do CSV |
| `src/Rscripts/weather-getter.r` | Clima atual e previsão de 5 dias de São Paulo pela Open-Meteo |

## Como executar

```bash
cd fase1/src
uv run main.py                         # programa de terminal
Rscript Rscripts/python-consumer.r     # estatística do CSV
Rscript Rscripts/weather-getter.r      # clima pela Open-Meteo
```

## Observações para a Fase 7

- `farm_math_handler.py` chama `input()` dentro do cálculo. Para um botão da dashboard disparar
  o cálculo, é preciso separar o cálculo da leitura do teclado (ver
  [plano de entrega](../plano-entrega/03-dashboard-central.md)).
- `weather-getter.r` executa `install.packages()` toda vez que roda; no `Rscript` isso exige um
  espelho do CRAN configurado.

## Material complementar

- [Resumo do artigo sobre VANTs na agricultura de precisão](fase1-resumo-artigo-vants.md)
