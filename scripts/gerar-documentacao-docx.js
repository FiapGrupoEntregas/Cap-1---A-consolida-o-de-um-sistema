const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, ImageRun,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, PageBreak,
  TableOfContents, LevelFormat, convertInchesToTwip, PageOrientation,
} = require("docx");

const RAIZ = "/home/ntl/workspace/SomposSprints";
const PRINTS = path.join(RAIZ, "document/evidencias/prints");
const VERDE = "2E7D32";
const CINZA = "555555";

// A4 com margem de 1", sobra 6,27" de largura útil.
const IMG_W = 600;                 // retrato: 6,27" úteis
const IMG_H = Math.round(600 / 2.005);
const IMG_W_L = 880;               // paisagem: ~9,17" úteis
const IMG_H_L = Math.round(880 / 2.005);

function p(texto, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 120, before: opts.before ?? 0 },
    alignment: opts.align,
    children: [new TextRun({ text: texto, size: opts.size ?? 22, bold: opts.bold,
      italics: opts.italics, color: opts.color, font: opts.font })],
  });
}

/** Parágrafo com trechos em negrito: partes(["texto ", ["negrito", true], " resto"]) */
function rico(partes, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 120 },
    children: partes.map((x) =>
      Array.isArray(x)
        ? new TextRun({ text: x[0], bold: true, size: opts.size ?? 22 })
        : new TextRun({ text: x, size: opts.size ?? 22 })),
  });
}

function h(texto, nivel) {
  return new Paragraph({
    heading: nivel,
    spacing: { before: nivel === HeadingLevel.HEADING_1 ? 360 : 240, after: 140 },
    children: [new TextRun({ text: texto, bold: true,
      color: nivel === HeadingLevel.HEADING_1 ? VERDE : "333333",
      size: nivel === HeadingLevel.HEADING_1 ? 30 : 25 })],
  });
}

function bullet(texto) {
  return new Paragraph({
    numbering: { reference: "lista", level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text: texto, size: 22 })],
  });
}

/** Figura: imagem + legenda numerada. */
let figura = 0;
function print(arquivo, legenda, paisagem = true) {
  figura += 1;
  const dados = fs.readFileSync(path.join(PRINTS, arquivo));
  const w = paisagem ? IMG_W_L : IMG_W;
  const hh = paisagem ? IMG_H_L : IMG_H;
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 160, after: 60 },
      // a legenda não pode ficar órfã: a imagem gruda no parágrafo seguinte
      keepNext: true,
      keepLines: true,
      children: [new ImageRun({ data: dados, type: "png",
        transformation: { width: w, height: hh } })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 240 },
      keepLines: true,
      children: [new TextRun({ text: `Figura ${figura} — ${legenda}`, size: 18,
        italics: true, color: CINZA })],
    }),
  ];
}

/** Tabela simples com cabeçalho verde. Larguras em DXA, somando 9026 (6,27"). */
function tabela(cabecalho, linhas, larguras) {
  const total = larguras.reduce((a, b) => a + b, 0);
  const celula = (texto, { negrito, fundo } = {}) =>
    new TableCell({
      width: { size: 0, type: WidthType.DXA },
      shading: fundo ? { type: ShadingType.CLEAR, fill: fundo, color: "auto" } : undefined,
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [new Paragraph({
        spacing: { after: 0 },
        children: [new TextRun({ text: texto, size: 19, bold: negrito,
          color: negrito && fundo === VERDE ? "FFFFFF" : "000000" })],
      })],
    });

  const linhaCabecalho = new TableRow({
    tableHeader: true,
    children: cabecalho.map((t, i) => {
      const c = celula(t, { negrito: true, fundo: VERDE });
      c.root[1] = c.root[1]; // no-op: larguras vão em columnWidths
      return c;
    }),
  });

  return new Table({
    columnWidths: larguras,
    width: { size: total, type: WidthType.DXA },
    rows: [
      linhaCabecalho,
      ...linhas.map((linha, idx) => new TableRow({
        children: linha.map((t) => celula(String(t), { fundo: idx % 2 ? "F4F6F4" : undefined })),
      })),
    ],
  });
}

const doc = new Document({
  creator: "Grupo AgriShield — FIAP 1TIAOB",
  title: "Sompo AgriShield — Documentação da entrega",
  description: "Sprint 4 do Challenge Sompo: MVP consolidado, com prints do sistema em funcionamento.",
  numbering: {
    config: [{
      reference: "lista",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: convertInchesToTwip(0.3), hanging: convertInchesToTwip(0.18) } } },
      }],
    }],
  },
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
  },
  sections: [
  {
    properties: { page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    children: [
      // ---------------------------------------------------------------- capa
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 1200, after: 200 },
        children: [new ImageRun({
          data: fs.readFileSync(path.join(RAIZ, "assets/logo-fiap.png")),
          type: "png", transformation: { width: 260, height: 74 },
        })],
      }),
      p("FIAP — Faculdade de Informática e Administração Paulista", { align: AlignmentType.CENTER, size: 20, color: CINZA, after: 600 }),
      new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { after: 100 },
        children: [new TextRun({ text: "Sompo AgriShield", bold: true, size: 56, color: VERDE })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { after: 400 },
        children: [new TextRun({ text: "Relevo × Clima", size: 32, color: "333333" })],
      }),
      p("“Um terreno inclinado que é seguro hoje pode capotar um trator amanhã.”",
        { align: AlignmentType.CENTER, italics: true, size: 22, color: CINZA, after: 700 }),
      p("Challenge Sompo Seguros — Sprint 4", { align: AlignmentType.CENTER, bold: true, after: 60 }),
      p("Documentação da entrega: o MVP em funcionamento", { align: AlignmentType.CENTER, color: CINZA, after: 700 }),

      tabela(
        ["Integrante", "RM", "Turma"],
        [
          ["Jonattas Felipe", "RM572692", "1TIAOB"],
          ["Natanael Filho", "RM572474", "1TIAOB"],
          ["Pedro Henrique", "RM571394", "1TIAOB"],
          ["Andrews Oliveira", "RM572311", "1TIAOB"],
        ],
        [4000, 2600, 2426],
      ),
      p("", { after: 200 }),
      p("Tutora: Sabrina Otoni", { align: AlignmentType.CENTER, size: 20, color: CINZA, after: 40 }),
      p("Setembro de 2026", { align: AlignmentType.CENTER, size: 20, color: CINZA, after: 300 }),
      p("Apresentação em vídeo (YouTube, não listado)", { align: AlignmentType.CENTER, size: 20, bold: true, after: 40 }),
      p("https://youtu.be/5-dttjN-_oI", { align: AlignmentType.CENTER, size: 20, color: VERDE }),

      new Paragraph({ children: [new PageBreak()] }),

      // ------------------------------------------------------------- sumário
      h("Sumário", HeadingLevel.HEADING_1),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 0 }, children: [new TextRun({ text: "1.  ", bold: true, size: 22, color: "2E7D32" }), new TextRun({ text: "O problema", size: 22, bold: true })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 0 }, children: [new TextRun({ text: "2.  ", bold: true, size: 22, color: "2E7D32" }), new TextRun({ text: "A solução, em quatro entregas", size: 22, bold: true })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 0 }, children: [new TextRun({ text: "3.  ", bold: true, size: 22, color: "2E7D32" }), new TextRun({ text: "Como o sistema está montado", size: 22, bold: true })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 0 }, children: [new TextRun({ text: "4.  ", bold: true, size: 22, color: "2E7D32" }), new TextRun({ text: "Onde há inteligência artificial no projeto", size: 22, bold: true })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 360 }, children: [new TextRun({ text: "4.1  ", bold: false, size: 22, color: "555555" }), new TextRun({ text: "O modelo preditivo, e o que ele mede", size: 22, bold: false })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 360 }, children: [new TextRun({ text: "4.2  ", bold: false, size: 22, color: "555555" }), new TextRun({ text: "Por que o alerta não vem do modelo", size: 22, bold: false })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 360 }, children: [new TextRun({ text: "4.3  ", bold: false, size: 22, color: "555555" }), new TextRun({ text: "A rede neural, e por que ela está desligada", size: 22, bold: false })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 0 }, children: [new TextRun({ text: "5.  ", bold: true, size: 22, color: "2E7D32" }), new TextRun({ text: "O sistema em funcionamento", size: 22, bold: true })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 360 }, children: [new TextRun({ text: "5.1  ", bold: false, size: 22, color: "555555" }), new TextRun({ text: "Mapa de risco — o relevo real da fazenda", size: 22, bold: false })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 360 }, children: [new TextRun({ text: "5.2  ", bold: false, size: 22, color: "555555" }), new TextRun({ text: "Mapa de risco — a previsão de 7 dias", size: 22, bold: false })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 360 }, children: [new TextRun({ text: "5.3  ", bold: false, size: 22, color: "555555" }), new TextRun({ text: "Equipamento ao vivo", size: 22, bold: false })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 360 }, children: [new TextRun({ text: "5.4  ", bold: false, size: 22, color: "555555" }), new TextRun({ text: "Maquinário — de qual máquina vem o alerta", size: 22, bold: false })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 360 }, children: [new TextRun({ text: "5.5  ", bold: false, size: 22, color: "555555" }), new TextRun({ text: "Subscrição — o terreno na cotação", size: 22, bold: false })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 360 }, children: [new TextRun({ text: "5.6  ", bold: false, size: 22, color: "555555" }), new TextRun({ text: "Relatórios — tendências por equipamento, região e cultura", size: 22, bold: false })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 360 }, children: [new TextRun({ text: "5.7  ", bold: false, size: 22, color: "555555" }), new TextRun({ text: "Replay de acidentes — a validação mais honesta", size: 22, bold: false })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 0 }, children: [new TextRun({ text: "6.  ", bold: true, size: 22, color: "2E7D32" }), new TextRun({ text: "O que este projeto não é", size: 22, bold: true })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 0 }, children: [new TextRun({ text: "7.  ", bold: true, size: 22, color: "2E7D32" }), new TextRun({ text: "Como executar", size: 22, bold: true })] }),
      new Paragraph({ spacing: { after: 70 }, indent: { left: 0 }, children: [new TextRun({ text: "8.  ", bold: true, size: 22, color: "2E7D32" }), new TextRun({ text: "Onde está o resto", size: 22, bold: true })] }),
      new Paragraph({ children: [new PageBreak()] }),

      // ------------------------------------------------------------ 1 problema
      h("1. O problema", HeadingLevel.HEADING_1),
      p("O seguro de máquinas agrícolas no Brasil é reativo: a seguradora só age depois do acidente. E um dos fatores que mais pesam no risco de uma máquina — o relevo — praticamente não é considerado na subscrição nem na operação."),
      p("Uma encosta de 12° é tranquila com o solo seco. Depois de 40 mm de chuva o solo perde aderência, e a mesma encosta passa a ter risco de capotamento e deslizamento. Nas baixadas a água acumula e a máquina atola. Os topos de morro concentram raios, e as cristas expostas pegam as rajadas mais fortes."),
      rico([["O mesmo terreno, portanto, muda de risco conforme o clima. "], "É essa variação que o AgriShield transforma em informação acionável — para o operador na máquina, para o gestor de frota e para o analista da seguradora."]),

      // ------------------------------------------------------------ 2 solução
      h("2. A solução, em quatro entregas", HeadingLevel.HEADING_1),
      rico([["Mapa de risco por talhão e por dia. "], "A partir da elevação por satélite (Copernicus DEM, via Open-Meteo), o sistema calcula inclinação, orientação e classe de terreno de cada pedaço da fazenda. Cruzando com a previsão do tempo, mostra por 7 dias onde e quando operar é perigoso — sempre com o motivo, em números."]),
      rico([["Limite de inclinação dinâmico na máquina. "], "A plataforma calcula o limite seguro do dia (por exemplo, 15° com solo seco e 10° com solo encharcado) e o envia por MQTT a um ESP32 instalado no equipamento, que mede a inclinação real e alerta o operador na hora — mesmo sem internet."]),
      rico([["Perfil de terreno para subscrição. "], "Na cotação, a seguradora vê um perfil objetivo do terreno (área íngreme, baixadas, áreas expostas e uma classe A/B/C), sem questionário e sem hardware."]),
      rico([["Registro da frota. "], "Cada máquina é cadastrada e vinculada ao dispositivo instalado nela, para se saber de qual máquina vem cada alerta."]),

      // --------------------------------------------------------- 3 arquitetura
      h("3. Como o sistema está montado", HeadingLevel.HEADING_1),
      p("Três camadas, com responsabilidades separadas — e a separação é verificável no código, não apenas declarada:"),
      tabela(
        ["Camada", "O que faz", "O que não faz"],
        [
          ["api/ (FastAPI)", "Calcula todo o risco, publica o limite, guarda telemetria e a trilha de auditoria", "—"],
          ["front-web/ (Streamlit)", "Exibe o que a API já calculou", "Nenhuma regra de negócio"],
          ["iot/ (ESP32, Wokwi)", "Mede a inclinação e aplica o limite recebido", "Não decide o limite"],
        ],
        [2100, 3800, 3126],
      ),
      p("", { after: 160 }),
      rico(["O fluxo de ponta a ponta é: ", ["Open-Meteo → API (motor de risco + SQLite) → MQTT → ESP32"], ", e de volta ", ["ESP32 → MQTT → API → front-web"], ". São 29 rotas REST e sete telas."]),
      rico(["Os limiares do motor de risco vivem em um documento só — ", ["document/regras-de-risco.md"], " — e o código os lê de lá, em vez de repetir números. Essa é a razão de cada alerta conseguir mostrar a conta que o gerou."]),

      // ------------------------------------------------------------------ 4 IA
      h("4. Onde há inteligência artificial no projeto", HeadingLevel.HEADING_1),
      p("Esta seção existe porque a pergunta tem três respostas neste projeto, e elas valem coisas diferentes. Misturá-las seria vender o que não temos."),
      tabela(
        ["Camada", "O que é", "Aprende com dados?", "Decide o alerta?"],
        [
          ["Motor de regras", "Limiares de chuva, vento, inclinação e solo, calibrados à mão", "Não", "Sim — é ele que manda"],
          ["Modelo preditivo", "Regressão logística treinada em 2.256 apólices reais do PSR/SISSER", "Sim", "Não — informa a seguradora"],
          ["Experimento MLP", "Rede neural pequena (8 neurônios, 1 camada), desligada por padrão", "Sim", "Não — nada"],
        ],
        [1900, 3600, 1800, 1726],
      ),
      p("", { after: 200 }),

      h("4.1 O modelo preditivo, e o que ele mede", HeadingLevel.HEADING_2),
      p("O modelo é uma regressão logística treinada sobre 2.256 apólices reais do seguro rural (PSR/SISSER, dados abertos do Ministério da Agricultura), com 22 variáveis de relevo e clima."),
      rico(["A avaliação usa ", ["divisão temporal"], ", não aleatória: treino até 2021 (1.447 linhas), validação em 2022–2023 (504) e teste em 2024 (305). Dados de safra têm tempo, e embaralhá-los vazaria o futuro para o passado. O limiar de decisão foi escolhido na validação e aplicado ao teste sem ajuste."]),
      tabela(
        ["Modelo", "AUC-PR no teste (2024)"],
        [
          ["Baseline por regras", "0,074"],
          ["Regressão logística (publicada)", "0,144"],
          ["Rede neural MLP (experimento)", "0,150"],
          ["Floresta aleatória", "0,196"],
        ],
        [5500, 3526],
      ),
      p("", { after: 160 }),
      rico(["O modelo publicado ", ["supera o baseline"], ": diferença de +0,070, com intervalo de confiança de 95% entre +0,003 e +0,169 (bootstrap pareado, 10.000 reamostragens). O intervalo quase toca o zero, e o teste tem apenas 26 sinistros — abaixo dos 30 que o próprio projeto definiu como mínimo para uma conclusão firme. As duas ressalvas estão escritas ao lado do número, na tela."]),

      h("4.2 Por que o alerta não vem do modelo", HeadingLevel.HEADING_2),
      p("Esta é a decisão técnica mais importante do projeto, e ela se sustenta num dado que o próprio modelo produz."),
      rico(["A variável que mais pesa na regressão logística é ", ["o estado (UF)"], ", com importância 0,0276 — quatro vezes a segunda colocada. O modelo aprendeu geografia de perda agrícola: seca no Nordeste, geada no Sul. Isso é útil para a seguradora precificar carteira, mas não serve para dizer a um operador se ", ["esta encosta, hoje"], ", é segura."]),
      rico(["O motivo de fundo é o rótulo disponível: a base pública registra ", ["sinistro de seguro agrícola"], " (perda de lavoura), não acidente de máquina. Um modelo treinado nesse rótulo aprende exposição climática de lavoura, incluindo seca e geada — que não são o perigo que o alerta trata."]),
      rico([["Por isso o alerta ao operador vem de regras explicáveis, e o modelo entra ao lado, nunca no lugar."], " Calibrar com a base de sinistros de máquinas da Sompo é o primeiro item do roadmap — e é exatamente o que a parceria destrava."]),

      h("4.3 A rede neural, e por que ela está desligada", HeadingLevel.HEADING_2),
      p("Foi treinada uma MLP pequena (uma camada oculta com 8 unidades, regularização alta) como experimento independente. Ela marcou AUC-PR de 0,150 no teste, contra 0,144 da regressão logística: empate dentro do ruído de um teste com 26 sinistros."),
      p("Por isso entrou como experimento isolado — artefato próprio, opt-in na API, e um botão na tela que começa desligado. Ela não participa de nível de risco, limite, recomendação ou alerta."),
      p("Uma pergunta previsível é por que não se adotou a floresta aleatória, que teve 0,196 no teste. Porque o conjunto de teste não seleciona modelo: a escolha se deu na validação, onde a floresta ficou 0,0045 abaixo da logística, contra um erro padrão de 0,0190 — empate técnico. Pela regra de um erro padrão, vence o candidato mais simples e explicável. Trocar por causa do teste faria o número dele deixar de significar qualquer coisa."),

    ],
  },
  {
    properties: { page: {
      size: { orientation: PageOrientation.LANDSCAPE },
      margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 },
    } },
    children: [
      // ---------------------------------------------------- 5 sistema em uso
      h("5. O sistema em funcionamento", HeadingLevel.HEADING_1),
      p("As capturas a seguir são do sistema rodando com dados reais: relevo do Copernicus DEM, previsão da Open-Meteo e 1.525.473 apólices do PSR/SISSER carregadas no banco."),

      h("5.1 Mapa de risco — o relevo real da fazenda", HeadingLevel.HEADING_2),
      p("O ponto de partida é o terreno. A fazenda é dividida numa grade de 10 × 10 células de aproximadamente 103 m × 110 m, e cada célula recebe elevação, inclinação, orientação e classe de terreno."),
      ...print("mapa-risco-analise-relevo.png",
        "Aba Relevo do Sítio Café da Serra (Carmo de Minas/MG): amplitude de 118 m, inclinação máxima de 21,6° e 17% da área com 15° ou mais. Quanto mais escura a célula, mais íngreme."),
      ...print("mapa-risco-analise-relevo-2.png",
        "A mesma grade colorida por classe de terreno, distinguindo baixada, encosta e topo exposto — as três situações que as regras tratam de formas diferentes."),

      h("5.2 Mapa de risco — a previsão de 7 dias", HeadingLevel.HEADING_2),
      p("Cruzando o relevo com a previsão do tempo, o mesmo talhão muda de cor ao longo da semana. Cada alerta traz a conta que o gerou."),
      ...print("mapa-risco-previsao-de-risco.png",
        "Previsão de risco com um dia aberto: 18% da área em nível alto, limite de inclinação do dia e os motivos em números — “Inclinação de 16,7° acima do limite de 15° (solo seco: 1,8 mm em 72 h)”. No rodapé, o cartão do modelo preditivo com a probabilidade e a métrica de comparação."),
      rico(["Observe o rodapé da figura: o cartão do modelo mostra a probabilidade ", ["ao lado"], " do nível por regras, com a linha “AUC-PR no teste: 0,144 contra 0,074 do baseline por regras”. A tela monta essa frase a partir do próprio artefato do modelo carregado, de modo que ela nunca discorde do que está servindo."]),

      h("5.3 Equipamento ao vivo", HeadingLevel.HEADING_2),
      p("O limite calculado é publicado por MQTT no ESP32, que mede a inclinação real e devolve telemetria e eventos. O painel se atualiza sozinho a cada dois segundos."),
      ...print("equipamento-live.png",
        "Painel do equipamento: faixa de nível, rolagem e arfagem medidas, limite aplicado no dispositivo, temperatura e umidade, e a lista de eventos recentes com os limites aplicados."),
      ...print("equipamento-live-2.png",
        "Continuação do painel: a seção Passaporte (prévia), que acumula horas operando, tempo acima do limite, alertas e capotamentos — a semente do Passaporte Digital que acompanharia a máquina na renovação, no sinistro e na revenda."),

      h("5.4 Maquinário — de qual máquina vem o alerta", HeadingLevel.HEADING_2),
      p("O identificador MQTT (tractor-01) identifica um ESP32, não um trator. O cadastro de maquinário separa as duas coisas e liga uma na outra. É a única parte do sistema em que o usuário escreve — por isso exige chave de API e fica registrada na trilha de auditoria."),
      ...print("maquinario-formulario.png",
        "Formulário de cadastro: código, nome, tipo, fabricante, modelo, ano, horímetro e o vínculo com o ESP32. O campo de observações traz aviso de LGPD, porque o cadastro descreve o bem, nunca a pessoa."),
      ...print("maquinario-cadastrado.png",
        "Ficha da máquina TRACTOR-01 (New Holland TL 75, 2020) com o dispositivo tractor-01 vinculado, o estado ao vivo dele e o histórico dos últimos 7 dias."),

      h("5.5 Subscrição — o terreno na cotação", HeadingLevel.HEADING_2),
      p("Para a seguradora, o mesmo relevo vira um perfil objetivo na hora da cotação: sem questionário e sem hardware instalado."),
      ...print("subscricao--sitio-cafe.png",
        "Perfil de subscrição: classe B com score 41,2/100, indicadores do terreno, a distribuição de inclinação e os drivers que mais pesaram. Em destaque, a nota declarando que os pesos da v1 ainda não foram calibrados com dados de sinistro."),
      rico(["Vale reparar na faixa azul da figura: o sistema ", ["declara que o score não está calibrado"], ". Publicar um número sem essa ressalva seria mais bonito e menos honesto."]),

      h("5.6 Relatórios — tendências por equipamento, região e cultura", HeadingLevel.HEADING_2),
      p("Três recortes, cada um com um campo que diz para quem serve e que decisão apoia."),
      ...print("relatorio-fazenda-sitio-cafe.png",
        "Aba Equipamento: horas operando, tempo acima do limite, alertas e capotamentos por dia, com exportação em CSV. Os números saem da telemetria do próprio dispositivo."),
      ...print("relatorios-regiao.png",
        "Aba Região: o histórico real de sinistros do PSR por UF e município, com as causas mais frequentes — apoia aceitar, precificar e priorizar inspeção."),
      ...print("relatorios-cultura.png",
        "Aba Cultura: 1.525.473 apólices, 358.370 sinistros e taxa de 23,5%, com as culturas ordenadas por taxa de sinistro e as causas do recorte."),
      rico(["Uma ressalva declarada na própria tela: o enunciado pede tendências por “equipamento, região ou ", ["tipo de operação"], "”. A base PSR/SISSER traz ", ["cultura agrícola"], ", não telemetria de operação — então o terceiro recorte é cultura, e o sistema diz isso em vez de deixar implícito."]),

      h("5.7 Replay de acidentes — a validação mais honesta", HeadingLevel.HEADING_2),
      p("O mesmo motor foi rodado na data e no local de cinco acidentes reais noticiados. A pergunta é direta: o sistema teria alertado?"),
      ...print("replay-acidente.png",
        "Placar do replay: 2 de 5 com alerta na célula do ponto e 3 de 5 em alguma célula da vizinhança, com o caso a caso e o link da notícia de cada um."),
      ...print("replay-acidente-formulario.png",
        "Replay em ponto e data manuais: o mesmo motor aplicado a qualquer coordenada e dia, para inspecionar o raciocínio fora dos casos pré-carregados."),
      rico(["O placar ", ["não é 5 de 5"], ", e os três “não” ficam à vista com o motivo — incêndio por falha mecânica não é o que este motor promete detectar. Mostrar um placar parcial e explicar as falhas vale mais que escolher casos que acertam."]),

    ],
  },
  {
    properties: { page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    children: [
      // ------------------------------------------------------- 6 limitações
      h("6. O que este projeto não é", HeadingLevel.HEADING_1),
      p("Declarado para não gerar expectativa errada:"),
      bullet("Não há hardware embarcado real. O ESP32 é simulado no Wokwi, com o sensor ajustado manualmente."),
      bullet("O modelo estima sinistro de seguro agrícola, não acidente de máquina. É a base pública que existe; calibrar com a base da Sompo é o roadmap."),
      bullet("O score de terreno da subscrição usa pesos da v1, escolhidos por julgamento de engenharia e ainda não calibrados com dados de sinistro."),
      bullet("Não é ambiente de produção: a demo usa broker MQTT público e leituras sem autenticação, o que está documentado com o que produção exigiria."),
      bullet("Nenhum dado pessoal entra no banco ou no repositório. Nomes e documentos do CSV público são descartados na leitura, com teste automatizado que falha se algo escapar."),

      // --------------------------------------------------------- 7 execução
      h("7. Como executar", HeadingLevel.HEADING_1),
      p("Em Docker, sem instalar Python nem dependências:"),
      new Paragraph({
        spacing: { after: 160 },
        shading: { type: ShadingType.CLEAR, fill: "F4F6F4", color: "auto" },
        children: [new TextRun({ text: "cp docker/.env.example .env", font: "Consolas", size: 20 })],
      }),
      new Paragraph({
        spacing: { after: 200 },
        shading: { type: ShadingType.CLEAR, fill: "F4F6F4", color: "auto" },
        children: [new TextRun({ text: "docker compose up --build", font: "Consolas", size: 20 })],
      }),
      rico(["O front abre em ", ["localhost:8501"], " e a documentação interativa da API em ", ["localhost:8000/docs"], ". O dispositivo é aberto à parte, no simulador Wokwi."]),
      rico(["A suíte de testes roda sem rede — a Open-Meteo e o MQTT são simulados: ", ["1.007 testes na API"], " e ", ["188 no front-web"], "."]),

      // ------------------------------------------------------ 8 documentação
      h("8. Onde está o resto", HeadingLevel.HEADING_1),
      p("Este documento é um retrato. O detalhe completo está no repositório:"),
      tabela(
        ["Documento", "O que responde"],
        [
          ["document/guia-do-projeto.md", "Panorama completo: cada feature, onde está o código e como vê-la funcionando"],
          ["document/dados-e-modelo.md", "Fontes, pipeline, features, métricas e as limitações do modelo"],
          ["document/regras-de-risco.md", "As fórmulas e os limiares do motor de risco"],
          ["document/arquitetura.md", "Componentes, fluxos e a lista de endpoints"],
          ["document/decisoes.md", "As 15 decisões de arquitetura e escopo, com contexto e consequências"],
          ["document/evidencias/", "Validações datadas: comando, saída real e veredito"],
        ],
        [3400, 5626],
      ),
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  const saida = path.join(RAIZ, "document/AgriShield-documentacao-da-entrega.docx");
  fs.writeFileSync(saida, buffer);
  console.log("gerado:", saida, (buffer.length / 1024 / 1024).toFixed(1) + " MB");
});
