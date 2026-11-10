# Roteiros dos três vídeos

Todos no YouTube como **não listado**; links no README da raiz e no `.txt`. Grave com a tela em
1080p, fonte do terminal grande (≥ 16) e fale o que está fazendo. Antes de cada gravação, deixe tudo
aberto em abas para não perder tempo carregando.

## Preparação comum (10 min antes)

```bash
cd Cap-1---A-consolida-o-de-um-sistema
python3 main.py fase4-api            # terminal 1
python3 main.py fase4-dashboard      # terminal 2 (reiniciada depois do .env apontar para a AWS)
python3 main.py listar               # terminal 3, para mostrar
```

Abas do navegador: dashboard (`localhost:8501`), e-mail com os alertas, console SNS (tópico
`farmtech-alertas`), console Lambda (`farmtech-alertas`), Rekognition demo, GitHub do repositório.
Feche notificações e outras janelas.

---

## Vídeo 1 — Entrega principal (até 10 min)

| Tempo | Tela | O que dizer |
|---|---|---|
| 0:00–0:40 | README no GitHub, rolando até a arquitetura | "FarmTech Solutions, Fase 7. Reunimos as Fases 1 a 6 num sistema só: uma pasta por fase, um `.env` único, um `main.py` que dispara qualquer serviço e a dashboard da Fase 4 evoluída para a central do sistema. Na segunda parte, um serviço de alerta na AWS." Mostre a tabela de status e o diagrama. |
| 0:40–1:20 | Terminal 3 | `python3 main.py listar`. "Cada serviço roda no próprio ambiente com uv, então as dependências não se misturam: o PyTorch da Fase 6 não encosta no Oracle da Fase 3." Rode `python3 main.py fase2-clima` e mostre o código S/L/C. |
| 1:20–2:00 | Dashboard → Início | "Esta é a dashboard central. A página Início mostra o estado do `.env`, da API, do Oracle e do alerta." Vá para a Central de serviços. |
| 2:00–2:50 | Central → Fase 1 | Manga, largura 100, comprimento 200, 10 ruas, 0,5 L/m → **Calcular**. "20 mil m² e mil litros de insumo, o mesmo cálculo do programa de terminal da Fase 1, agora sem perguntas." Se tiver R instalado, clique em Estatística (R). |
| 2:50–3:30 | Central → Fase 2 | **Previsão do tempo → código S/L/C**. "A Open-Meteo responde a previsão de chuva e o código vai para o ESP32 do Wokwi, que decide a irrigação." Aponte o circuito ao lado. |
| 3:30–4:20 | Central → Fase 3 | **Consultar o Oracle**. "Sete consultas do `consulta.sql` rodando no Oracle da FIAP, direto da dashboard." Clique em **Iniciar** a dashboard da Fase 3 e abra o link na 8502 por 10 segundos. |
| 4:20–5:10 | Análise de solo (Fase 4) | "A dashboard original da Fase 4 continua aqui, sem mudanças: busca o mês na API, treina a Random Forest e prevê o próximo ciclo." Clique em **Buscar e treinar modelo** com um mês que tenha dados. |
| 5:10–6:00 | Central → Fase 6 | Escolha `trator_02.jpg` (ou envie uma foto) → **Detectar**. "O YOLOv5 que treinamos na Fase 6 virou um serviço: recebe a imagem e devolve classe, confiança e caixa. O JSON também traz uma ação sugerida para o alerta." |
| 6:00–7:30 | Central → Alerta, depois o e-mail | "Parte 2: o serviço de alerta. Ele lê as últimas leituras de `SOIL_DATA`, aplica regras de umidade, pH e NPK e publica no Amazon SNS com a ação corretiva." Escolha "últimas leituras do Oracle", marque **Forçar reenvio** → **Verificar sensores e alertar**. Mostre a tabela de alertas e o `message_id`. Troque para a aba do e-mail e leia o problema e a ação corretiva. |
| 7:30–8:40 | Console AWS: SNS → Lambda | SNS: tópico, assinatura confirmada, aba Monitoring. "Na AWS, o tópico `farmtech-alertas` com a assinatura de e-mail confirmada, e um usuário IAM que só pode publicar nele." Lambda: aba Test → **Test** → sucesso → novo e-mail. "As mesmas regras também rodam dentro da AWS, numa Lambda." |
| 8:40–9:30 | README → seção de alertas com os prints | "Os prints comentados estão no README, junto com as regras e a arquitetura." |
| 9:30–10:00 | README → topo | "Trocando as bases de dados e as regras, o mesmo sistema atende outro setor: a dashboard, o `main.py` e o alerta não dependem de agricultura. Integrantes: [nomes e RMs]. Obrigado." |

Se passar de 10 min, corte primeiro a Fase 3 (4:20) e a Análise de solo (5:10).

---

## Vídeo 2 — Ir Além 1: Amazon Rekognition (até 4 min)

Use a apresentação de slides "Rekognition vs YOLO FarmTech" nos trechos indicados.

| Tempo | Tela | O que dizer |
|---|---|---|
| 0:00–0:30 | Slide 1 e 2 | "Ir Além 1. Pergunta: um serviço pronto da AWS, o Rekognition, substitui o YOLO que treinamos na Fase 6? Testamos os dois nas mesmas quatro fotos." |
| 0:30–1:15 | Console Rekognition → Label detection → upload `vaca_02.jpg` | "Sem treinar nada: Animal, Cattle, Cow, Dairy Cow, 99,9%, e a caixa da vaca. O painel Response mostra o JSON que o nosso script recebe." Abra **Response** e role até `Instances` e `BoundingBox`. |
| 1:15–2:00 | Terminal | `python3 main.py ir-alem-1 --comparar`. "O script manda as fotos ao Rekognition com boto3, salva o JSON, desenha as caixas e roda o YOLO da Fase 6 nas mesmas fotos." Mostre o JSON de resumo. |
| 2:00–2:50 | Slide 3 (tabela) e slide 4 (imagens lado a lado) | "Os dois acertaram as quatro classes. O Rekognition com mais confiança: 90 a 99% contra 60 a 84%. Mas repare no trator: o Rekognition dá o rótulo Tractor com 90% e **não desenha a caixa do trator**; ele marca rodas, pessoa e pássaros. Na segunda foto chama de Bulldozer. O YOLO desenha o trator inteiro, porque foi treinado para isso." |
| 2:50–3:30 | Slide 5 (comparação crítica) | "Facilidade: Rekognition ganha, dez linhas de código e zero treino. Especificidade e localização: YOLO ganha. Custo: US$ 0,001 por imagem e internet, contra um modelo que roda offline e pode ir para a borda." |
| 3:30–4:00 | Slide 6 e IAM/política | "Para a FarmTech: Rekognition para começar a monitorar sem equipe de ML; YOLO próprio quando a classe é do negócio. Os dois alimentam o mesmo alerta. Permissão mínima no IAM: só `DetectLabels`." |

---

## Vídeo 3 — Ir Além 2: algoritmo genético (até 4 min)

Abra antes: `cd IR-ALEM/ir-alem-2 && uv run jupyter lab ir_alem_2_algoritmo_genetico.ipynb`, com o
notebook já executado (não rode ao vivo; mostre as saídas).

| Tempo | Célula | O que dizer |
|---|---|---|
| 0:00–0:40 | Seção 1 e tabela dos talhões | "Ir Além 2. Os sensores dizem o que fazer em cada talhão, mas o orçamento não cobre tudo. Quais intervenções executar para o maior ganho? Mochila binária com 69 itens, 2^69 combinações, montada das leituras reais de `SOIL_DATA`." |
| 0:40–1:10 | Itens por ação e orçamento | "Cada regra que dispara vira um item com custo por hectare e benefício proporcional ao déficit e à área. Orçamento: 35% do custo total." |
| 1:10–2:00 | Código do AG (seleção, cruzamento, mutação) | "AG do zero em NumPy. Duas variantes de cada operador: torneio ou roleta, um ponto ou uniforme, bit-flip ou troca. Elitismo, penalidade proporcional ao excesso e um reparo final que garante um plano dentro do orçamento." |
| 2:00–2:30 | Tabela de validação | "Numa instância de 18 itens, o AG encontra o mesmo ótimo da força bruta em 0,04 s contra 0,5 s." |
| 2:30–3:15 | Figuras 02 e 03 | "Oito configurações, dez sementes. A seleção é o que mais pesa: torneio vence roleta em todas as combinações. Cruzamento e mutação mudam pouco." |
| 3:15–3:50 | Plano final e figura 05 | "24 intervenções, 100% do orçamento, 59% do benefício possível com 35% do custo, 99,8% da heurística gulosa. Irrigação nos talhões mais secos e P e K onde o nível é zero." |
| 3:50–4:00 | Seção 8 | "Trocando o CSV e a tabela de custos, o mesmo notebook decide manutenções de frota ou campanhas com verba fixa." |
