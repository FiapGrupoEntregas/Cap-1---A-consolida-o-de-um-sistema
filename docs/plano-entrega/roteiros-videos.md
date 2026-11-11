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

O vídeo percorre o notebook na ordem das seções. Para cada uma há três partes:

- **Tela:** o que mostrar e onde parar o mouse.
- **Para entender:** o que está acontecendo ali, só para você. Não precisa falar.
- **Fala:** o texto para ler. São cerca de 640 palavras, perto de 4 minutos em ritmo normal. Ensaie uma
  vez cronometrando.

### Preparação

```bash
cd IR-ALEM/ir-alem-2
uv run jupyter lab ir_alem_2_algoritmo_genetico.ipynb
```

- O notebook já está executado. Não rode ao vivo; só role e mostre as saídas.
- Zoom do navegador em 125 % para as tabelas ficarem legíveis.
- Recolha o código das células que só desenham gráficos (as das figuras 02 a 05 e da arquitetura):
  clique na barra azul à esquerda da célula. Assim aparece só a figura.
- Os números abaixo são os da execução atual. Se você reexecutar, os tempos mudam um pouco: leia o
  que estiver na tela.

---

### 0:00–0:30 · Seção 1 — O problema (e a tabela dos talhões)

**Tela:** título do notebook, texto da seção 1. Role até a tabela com os 20 talhões e passe o mouse
pelas colunas `umidade`, `ph`, `n`, `p`, `k` e `area_ha`.

**Para entender:** cada linha é uma leitura real da tabela `SOIL_DATA` do Oracle (Fase 4). O script
`gerar_dados.py` buscou as 20 mais recentes, chamou cada uma de "talhão" e sorteou uma área entre 2 e
12 hectares com semente fixa. O notebook só lê o CSV, por isso qualquer um reproduz sem acesso ao banco.

**Fala:**
> "Ir Além 2 da FarmTech. Os sensores da Fase 4 mostram, talhão por talhão, solo seco, pH fora da
> faixa e falta de nutrientes, e o serviço de alerta diz o que fazer em cada um. Só que o orçamento da
> semana não cobre tudo. A pergunta é: quais intervenções executar para ter o maior ganho sem estourar
> a verba? A entrada são as 20 leituras mais recentes da tabela SOIL_DATA, e cada uma vira um talhão."

### 0:30–0:50 · Seção 1.1 — Normalização das leituras

**Tela:** texto da 1.1 e a tabela logo abaixo. Compare T01 (N 63,9) com T10 (N 25,0).

**Para entender:** no banco há duas escalas. T01 a T09 vieram do endpoint `/simulate` da API, que
grava N, P e K de 0 a 255 (por isso no CSV aparecem 163, 190…). T10 a T20 vieram do ESP32, que grava
em porcentagem. A célula converte tudo para porcentagem. Os alvos são os mesmos das regras do alerta;
para nutriente usa 50 %, não os 30 % do alerta, porque o plano mira o ideal e não só o mínimo.

**Fala:**
> "Primeiro, um ajuste. No banco convivem duas escalas de N, P e K: o ESP32 grava em porcentagem e o
> simulador da API grava de 0 a 255. Os talhões T01 a T09 vêm do simulador, então convertemos tudo para
> porcentagem. Os alvos vêm das regras do alerta: umidade mínima de 60 %, pH entre 6 e 6,8, e nutriente
> desejável em 50 %."

### 0:50–1:20 · Seção 1.2 — Itens da mochila

**Tela:** texto da 1.2, depois a saída da célula: a linha "69 intervenções candidatas…" e a tabela
agrupada por ação. Aponte as linhas `calagem` e `enxofre`.

**Para entender:** cada regra que dispara num talhão vira um "item".

- **Custo** = preço por hectare da ação × área.
- **Benefício** = déficit (quanto falta até o alvo) × peso de importância × área.

Exemplo: T03 tem umidade 45 e alvo 60, déficit 15. Irrigar custa 120 × 10,6 ha = R$ 1.272 e rende
15 × 1,6 × 10,6 = 254,4 de benefício. Escolher o subconjunto que cabe na verba e soma mais benefício é
o problema da mochila. Calagem e enxofre custam R$ 54 mil juntos e rendem só 468 de benefício, porque o
pH está quase no alvo. É uma pista do que o algoritmo vai descartar.

**Fala:**
> "Cada regra que dispara vira um item da mochila. O custo é o preço por hectare vezes a área. O
> benefício é o déficit, quanto falta até o alvo, vezes um peso de importância, vezes a área. Saem 69
> intervenções que custariam 150 mil reais, e o orçamento é 35 % disso, 52 mil. São 2 elevado a 69
> combinações, umas 6 vezes 10 elevado a 20: impossível testar uma a uma. Repare que calagem e enxofre
> custam caro e rendem pouco; o algoritmo vai ter que descobrir isso sozinho."

### 1:20–2:05 · Seção 2 — O algoritmo genético

**Tela:** tabela dos operadores no texto da seção 2. Depois role devagar pelo código, parando em
`aptidao`, `selecao_torneio`, `cruzamento_um_ponto`, `mutacao_bitflip`, `algoritmo_genetico` e
`reparar`. A saída da célula (24 intervenções dentro da verba) pode aparecer rapidamente, sem comentar.

**Para entender:**

- **Indivíduo:** um plano, ou seja, 69 zeros e uns. 1 = executar aquela intervenção.
- **Aptidão:** soma dos benefícios. Se o plano passa do orçamento, perde pontos proporcionais ao
  excesso. Não é descartado, porque um plano que passou por pouco ainda tem boas escolhas.
- **Ciclo de cada geração:** os 4 melhores passam intactos (elitismo); o resto nasce de seleção dos
  pais, cruzamento e mutação. São 120 planos por 200 gerações.
- **Variantes:** torneio sorteia 3 e leva o melhor; roleta sorteia com chance proporcional à aptidão.
  Um ponto corta os dois pais num lugar e troca as metades; uniforme decide gene a gene. Bit-flip inverte
  genes ao acaso; troca permuta dois genes e mantém o número de itens.
- **Reparo:** no fim, se o melhor plano ainda passa da verba, tira os itens de pior custo-benefício até
  caber. Assim o resultado é sempre viável.

**Fala:**
> "O algoritmo genético, feito do zero em NumPy. Cada indivíduo é um plano: 69 zeros e uns, em que 1
> significa executar a intervenção. A aptidão é a soma dos benefícios; se o plano estoura o orçamento,
> perde pontos proporcionais ao excesso, em vez de ser descartado, porque um plano quase viável ainda
> tem bons genes. A cada geração os 4 melhores passam direto, que é o elitismo, e o resto nasce de
> seleção, cruzamento e mutação. Cada operador tem duas variantes: torneio ou roleta, um ponto ou
> uniforme, bit-flip ou troca. No fim, um reparo tira os itens de pior custo-benefício até o plano caber
> na verba."

### 2:05–2:30 · Seção 3 — Validação

**Tela:** texto da seção 3 e a tabela de três linhas: força bruta, guloso e algoritmo genético.

**Para entender:** no problema completo não dá para saber qual é o melhor plano de verdade. Então a
célula pega só os 18 itens mais caros (2^18 = 262.144 combinações), onde a força bruta testa todas e
acha o ótimo garantido. O AG chegar ao mesmo número prova que ele funciona. A gulosa ordena os itens
por benefício/custo e vai pegando enquanto cabe; é a referência clássica da mochila.

**Fala:**
> "Como saber se o AG acerta? Numa versão menor, com 18 itens, a força bruta testa todas as 262 mil
> combinações e acha o ótimo garantido. O AG chega exatamente ao mesmo valor, 3.514,75, em 0,03 segundo
> contra 0,55 da força bruta. A heurística gulosa também acerta aqui; ela é a referência clássica para
> esse problema."

### 2:30–3:10 · Seção 4 — Comparação das variantes

**Tela:** tabela de resumo (aponte que as quatro primeiras linhas são torneio), depois as três figuras
na ordem: convergência (02), boxplot por operador (03) e qualidade × tempo (04).

**Para entender:** são 2 × 2 × 2 = 8 configurações, cada uma rodada com 10 sementes para tirar o efeito
da sorte. "% do melhor" compara com o melhor valor que qualquer execução achou.

- **Figura 02:** todas as curvas sobem e estabilizam bem antes da geração 200.
- **Figura 03:** um boxplot por operador. Em seleção, a caixa do torneio fica acima da roleta. Em
  cruzamento e mutação as caixas quase se sobrepõem.
- **Figura 04:** tudo roda em décimos de segundo. A troca é mais lenta porque é um laço em Python; o
  bit-flip é uma operação vetorizada do NumPy.
- **Por que a roleta perde:** no fim da busca os planos têm aptidões parecidas, então a roleta dá
  chances quase iguais a todos e para de favorecer os melhores. O torneio sempre leva o melhor dos 3.

**Fala:**
> "Agora a comparação: as 8 combinações de operadores, cada uma com 10 sementes, no problema completo.
> A tabela está ordenada pela aptidão média, e as quatro primeiras são todas com torneio. Na
> convergência, todas as curvas estabilizam bem antes das 200 gerações. No boxplot fica claro que a
> seleção é o que mais pesa: torneio acima da roleta, porque a roleta perde força quando os planos ficam
> parecidos. Cruzamento e mutação quase não mudam o resultado."

### 3:10–3:35 · Seção 5 — O plano de manejo escolhido

**Tela:** as quatro linhas de texto da saída, a tabela do plano (24 linhas) e a figura 05. Na figura,
aponte as barras claras (o que era possível) e as fortes (o que foi escolhido).

**Para entender:** o AG, sem ninguém dizer, escolheu pela ordem de custo-benefício por hectare:

| Ação | Benefício por R$ | Escolhida? |
|---|---|---|
| Irrigar talhão bem seco (umidade 44–46) | ≈ 0,19–0,21 | sim |
| Adubar K (nível zero) | 0,156 | sim, em todos os 11 |
| Adubar P (nível zero) | 0,147 | sim, em 7 |
| Irrigar talhão pouco seco (umidade 50) | 0,133 | só no T19 |
| Adubar N (nível 25, déficit menor) | 0,108 | não |
| Calagem e enxofre (pH quase no alvo) | ≈ 0,01 | não |

É o que um agrônomo faria olhando a tabela, mas o AG chegou lá sem enumerar combinações.

**Fala:**
> "Com a melhor configuração, torneio, um ponto e troca, sai o plano da semana: 24 das 69 intervenções,
> usando 100 % do orçamento. Ele captura 59 % de todo o benefício possível gastando só 35 % do custo, e
> fica a 99,8 % da gulosa. No gráfico, o claro é o que era possível e o forte é o que foi escolhido:
> irrigação nos talhões mais secos, potássio e fósforo onde o nível é zero, e nada de calagem nem
> enxofre, que custam caro e rendem pouco."

### 3:35–3:45 · Seção 6 — Arquitetura

**Tela:** a figura com as seis caixas.

**Para entender:** é o fluxo do notebook num desenho só, exigido como figura autoral.

**Fala:**
> "A arquitetura resume o caminho: do Oracle ao CSV, das regras aos itens, do algoritmo genético ao
> plano, com a validação no fim."

### 3:45–3:50 · Seção 7 — Parâmetros

**Tela:** a tabela de parâmetros. Não leia linha por linha; só mostre.

**Para entender:** cada valor tem a justificativa ao lado. Se o professor perguntar, os dois mais
interessantes são a mutação de 1/n (em média um gene por plano) e a população inicial com 30 % dos
itens ligados (perto do que cabe na verba; com 50 % todos nasciam estourando o orçamento).

**Fala:**
> "Cada parâmetro está justificado nesta tabela."

### 3:50–4:00 · Seção 8 — Conclusões

**Tela:** os tópicos das conclusões e o parágrafo final sobre outros setores.

**Fala:**
> "Concluindo: o AG acha o ótimo onde dá para conferir e fica colado na gulosa no problema completo. A
> vantagem dele é que basta mudar a aptidão para incluir novas regras, como limite de horas de máquina.
> Trocando o CSV e os custos, o mesmo notebook decide manutenção de frota ou campanhas com verba fixa.
> Obrigado."

---

**Se passar de 4 minutos:** corte a fala da seção 7 e encurte a da seção 4 para a frase sobre o
boxplot.

**Se perguntarem "por que não usar só a gulosa, se ela é quase igual?":** a gulosa só funciona bem na
mochila simples. Com uma regra a mais, por exemplo "não irrigar e adubar o mesmo talhão na mesma
semana" ou um limite de mão de obra por dia, ela deixa de servir. O AG continua funcionando só
mudando a função de aptidão.
