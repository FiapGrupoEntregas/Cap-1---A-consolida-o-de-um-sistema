# 27/09/2026 — Desempenho do mapa (US-03, critério 7)

O critério 7 da US-03 pede: *"a resposta do mapa sai em **menos de 3 s sem cache** e **menos de
200 ms com cache**"*. Ele estava marcado como **não medido** em
[user-stories.md](../user-stories.md) desde 21/09, quando a tentativa foi **abortada de propósito**:
a cota diária da Open-Meteo estava esgotada, e medir naquele estado mediria a **recusa da
Open-Meteo**, não o mapa.

Hoje a cota estava disponível (confirmado por `GET /devices/tractor-01/limit` respondendo 200 antes
de medir), então a medição foi feita.

## Como foi medido

```bash
uv run --project api python scripts/medir_mapa.py --saida document/evidencias/2026-09-27-medicao-mapa.json
```

O script ([`scripts/medir_mapa.py`](../../scripts/medir_mapa.py)) sobe a API num processo próprio,
com **cache vazio** e **MQTT desligado**, e para cada fazenda mede:

- a **primeira** chamada de `/terrain` e de `/risk` — *fria*, que vai até a Open-Meteo;
- **cinco** repetições — *quentes*, servidas do `TTLCache` em memória.

Antes de medir qualquer coisa ele confere se a Open-Meteo responde, e **recusa rodar** se a cota
estiver esgotada. Essa guarda é o que separa esta medição da tentativa de 21/09.

## Resultado

| Fazenda | Rota | Frio | Quente (mediana) | Quente (pior) | HTTP |
|---|---|---:|---:|---:|---:|
| cafe-carmo-de-minas | `terrain` | 828,2 ms | 1,6 ms | 9,1 ms | 200 |
| cafe-carmo-de-minas | `risk` | 252,0 ms | 41,6 ms | 42,9 ms | 200 |
| graos-sorriso | `terrain` | 215,1 ms | 2,9 ms | 3,5 ms | 200 |
| graos-sorriso | `risk` | 358,1 ms | 39,1 ms | 47,2 ms | 200 |
| uva-serra-gaucha | `terrain` | 207,5 ms | 4,1 ms | 8,0 ms | 200 |
| uva-serra-gaucha | `risk` | 356,1 ms | 38,9 ms | 42,2 ms | 200 |

**Pior caso frio: 828,2 ms** (limite 3.000 ms) · **pior caso quente: 47,2 ms** (limite 200 ms).

## ✅ Critério 7 atendido, com margem

O pior caso frio ficou em **28% do orçamento** e o pior quente em **24%**. Os números brutos das
seis medições, com as cinco repetições de cada uma, estão em
[`2026-09-27-medicao-mapa.json`](2026-09-27-medicao-mapa.json).

## O que esta evidência **não** cobre

- **É tempo de API, não de tela.** Mede a resposta HTTP; o desenho do mapa `pydeck` no navegador
  soma tempo em cima disso e não foi medido.
- **Uma execução, numa máquina.** Não é percentil de carga: é a verificação de um critério de
  aceite com ordem de grandeza folgada, não um teste de desempenho.
- **A primeira chamada é "fria" só quanto ao cache da API.** A Open-Meteo tem cache próprio do lado
  dela, então o tempo frio real de um usuário pode variar com o que ela já tem quente.
- **O cache é em memória.** Reiniciar o processo da API zera o aquecimento — motivo pelo qual
  `run-demo.sh --aquecer` precisa rodar com a API que vai ficar no ar durante a demo.
