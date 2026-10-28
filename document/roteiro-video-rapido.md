# Roteiro rápido do vídeo — uma página, para ter aberta enquanto grava

> Versão condensada de [roteiro-video.md](roteiro-video.md), que continua sendo a fonte completa
> (ressalvas, origem de cada número e checklist longo). Aqui é só o essencial para gravar.
>
> **4 min 45 s** em 10 blocos. Limite: 5:00.

## Antes de apertar o REC (5 minutos)

1. `./scripts/run-demo.sh --aquecer` — API e front no ar, cache quente
2. Abrir **Subscrição**, **Relatórios** e **Replay** uma vez — a primeira carga é a lenta
3. Wokwi rodando, com `[mqtt] conectado` no Serial e o painel em 🟢 **Online**
4. Navegador em tela cheia, zoom **110–125%**, notificações desligadas, 1080p
5. Conferir na tela: o **placar do replay**, a **métrica no cartão do modelo** e o **% de células
   vermelhas** — os três mudam, e você vai falar o número que estiver lá

## Os 10 blocos

| # | Tempo | Tela | O que dizer (ideia, não decoreba) |
|---|---|---|---|
| **1** | 0:00–0:22 | Trator em encosta + título | O seguro de máquina agrícola paga **depois** do acidente. E o fator que mais pesa, o **relevo**, quase não é considerado. Uma encosta de 12° é tranquila com solo seco; depois de 40 mm de chuva, capota trator. |
| **2** | 0:22–0:45 | Diagrama de arquitetura | Cruzamos **relevo por satélite** com **previsão do tempo**, calculamos risco por talhão e por dia, e mandamos o **limite de inclinação do dia** para um dispositivo na máquina. Tudo com regras explicáveis: todo alerta mostra o motivo, em números. |
| **3** | 0:45–1:25 | Mapa de risco → Relevo, depois Previsão. Trocar Carmo de Minas ↔ Sorriso | Este é o relevo **real**, de satélite. Com a chuva prevista, no café em Carmo de Minas **_(leia o % da tela)_** das células ficam vermelhas. Em Sorriso, terreno plano, os sete dias ficam verdes. **Mesma chuva, resultados opostos** — o que muda é o relevo. |
| **4** | 1:25–1:48 | Rolar até o cartão **Probabilidade de sinistro (modelo)** | Ao lado da regra, um **modelo treinado com sinistros reais** dá uma segunda leitura para a seguradora. No teste de 2024 ele **supera** o baseline — **por pouco, com 26 sinistros**, e porque o conjunto de teste dobrou, não porque o modelo melhorou. Por isso o alerta ao operador continua vindo da **regra explicável**. |
| **5** | 1:48–2:15 | Equipamento ao vivo → card do limite → **Enviar ao equipamento** | O limite seguro não é fixo: cai quando o solo encharca. A plataforma calcula o limite do dia e **publica para a máquina** por MQTT, com mensagem retida — o equipamento recebe o último limite assim que liga. |
| **6** | 2:15–3:00 | Wokwi ao lado do painel: (a) Serial conectado, (b) MPU a ~12° → LED + buzzer + OLED, (c) ~60° → capotamento | O ESP32 mede a inclinação e alerta o operador **na hora, sem internet** — o limite fica gravado no dispositivo. Se o pior acontecer, ele detecta o capotamento e manda o evento com **30 segundos de contexto**. |
| **7** | 3:00–3:30 | Subscrição (classe A/B/C) → Relatórios (as 3 abas) | Para a seguradora, o mesmo relevo vira duas coisas. Na **cotação**, um perfil objetivo do terreno, sem questionário e sem hardware. Na carteira, **tendências por equipamento, região e cultura**, sobre 1,5 milhão de apólices reais, com CSV. |
| **8** | 3:30–3:55 | Replay → caso de Imbituva → placar do topo | Rodamos o motor na data e no lugar de **cinco acidentes reais**. O placar **não** é cinco de cinco: **dois de cinco no ponto**, três na vizinhança. Em Imbituva o motor apontou risco de raio no dia em que um raio matou. E os três "não" ficam à vista, com o motivo. |
| **9** | 3:55–4:22 | Terminal com `count(*)` · `GET /api/v1/audit` no `/docs` · saída do `pytest` | Carregamos **1.525.473 apólices reais** do seguro rural, dados abertos. Nomes e documentos são descartados na leitura. **Toda decisão** fica registrada com entrada, saída e a versão da regra e do modelo, e escrever exige chave de API. São **_(recontar hoje)_** testes automatizados, todos offline. |
| **10** | 4:22–4:45 | Slide: pronto · próximo passo · integrantes | Está no ar: mapa de risco, limite na máquina, telemetria e capotamento, cadastro da frota, subscrição, relatórios, replay, base real e trilha de auditoria. O próximo passo é **calibrar**: o rótulo que temos é sinistro de **seguro agrícola**, não de máquina. Calibrar com a base da Sompo é o que a parceria destrava. |

## Cinco coisas para não errar

1. **Nunca diga "o modelo venceu" e pare aí.** A frase do bloco 4 já vem com a ressalva colada —
   mantenha as duas juntas. Se a banca perguntar, a resposta longa está em
   [dados-e-modelo.md](dados-e-modelo.md#resultados-do-modelo-d3).
2. **Todo número dito tem de estar na tela naquele instante.** Nada de métrica de cabeça: o cartão
   do modelo lê o artefato em tempo de execução e a previsão muda todo dia.
3. **Se usar o cenário simulado de chuva, diga em voz alta que é simulado.**
4. **Narração humana**, sem TTS, sem música por cima da voz.
5. **Se estourar 5:00, corte no bloco 9** — nunca no 4 nem no 8, que são o que o enunciado cobra.

## Depois de publicar

- YouTube como **"Não listado"**; teste o link numa janela anônima
- Cole o link no `README.md` da raiz **e** em [roteiro-video.md](roteiro-video.md)
- Cartela com os nomes dos integrantes no vídeo

**Link do vídeo:** https://youtu.be/5-dttjN-_oI
