# 📚 Documentação técnica — Sompo AgriShield

Aqui ficam as práticas e decisões que **todo o time segue**. Na dúvida, vale o que está escrito aqui.

> **Onde fica cada coisa**
> - `document/`: documentação técnica e práticas do projeto (esta pasta)
> - `feature/`: especificação de cada feature (o que fazer e como aceitar)
> - `docker/`: como rodar em container ([docker/README.md](../docker/README.md))
> - `.claude/`: agentes e skills do Claude Code (ver [fluxo-agentes.md](fluxo-agentes.md))

## 🚩 Comece por aqui

| Documento | Para que serve |
|---|---|
| [AgriShield-documentacao-da-entrega.docx](AgriShield-documentacao-da-entrega.docx) | **Documento de entrega em Word**, com os 14 prints do sistema funcionando e a descrição do projeto — do problema à IA, com as limitações declaradas. É o que se entrega a quem não vai clonar o repositório |
| [guia-do-projeto.md](guia-do-projeto.md) | **Panorama completo em um documento só:** problema, arquitetura, o que está implementado (com o código e como ver funcionando), onde há IA, decisões, execução do zero e limitações |

Se você tem cinco minutos, leia só esse. Os demais respondem perguntas específicas.

## 🧠 O produto: regras, dados e contratos

| Documento | Responde |
|---|---|
| [regras-de-risco.md](regras-de-risco.md) | Como o risco é calculado: fórmulas e limiares. **Fonte única** — o código não inventa valores |
| [dados-e-modelo.md](dados-e-modelo.md) | De onde vêm os dados reais, como o dataset é montado, o que o modelo mede e o que ele **não** prova |
| [arquitetura.md](arquitetura.md) | Componentes, fluxos de dados e a lista de endpoints da API |
| [esquema-do-banco.md](esquema-do-banco.md) | **A estrutura do banco**: as 8 tabelas, colunas, índices, chaves únicas, retenção e o porquê de cada escolha |
| [contrato-mqtt.md](contrato-mqtt.md) | Tópicos e payloads entre o ESP32 e a API. **Mudou aqui, muda o firmware e a API juntos** |
| [user-stories.md](user-stories.md) | As histórias por perfil e a matriz história → feature → arquivo → evidência → situação |

## ▶️ Rodar e apresentar

| Documento | Responde |
|---|---|
| [ambiente-de-desenvolvimento.md](ambiente-de-desenvolvimento.md) | Como instalar e rodar tudo (uv, pip, PlatformIO, Wokwi), e o atalho em Docker |
| [../docker/README.md](../docker/README.md) | Rodar em container, semear a base e por que o ESP32 fica fora |
| [roteiro-de-testes.md](roteiro-de-testes.md) | **12 blocos de teste do MVP com a IA como fio condutor**: o que fazer, o que esperar, o que cada um prova sobre IA e qual print sai dali. Traz três montagens prontas (vídeo de 5 min, demo ao vivo, defesa técnica) |
| [demo.md](demo.md) | Roteiro da apresentação **ao vivo**, checklist e plano B |
| [roteiro-video.md](roteiro-video.md) | Roteiro do **vídeo de entrega** (até 5 min): blocos, tempos, quem narra e o que aparece na tela |
| [roteiro-video-rapido.md](roteiro-video-rapido.md) | **Uma página** com os 10 blocos, o pré-voo e as cinco coisas para não errar — é a versão para ter aberta enquanto grava |

## 🧭 Decisões, entrega e evidências

| Documento | Responde |
|---|---|
| [decisoes.md](decisoes.md) | Por que o projeto é assim: as decisões de arquitetura e de escopo (ADRs). **Material de pitch** |
| [CHECKLIST-DA-ENTREGA.md](CHECKLIST-DA-ENTREGA.md) | **O que ainda falta fazer para entregar**, com a ação exata e o tempo de cada uma. Comece por aqui na reta final |
| [entregaveis.md](entregaveis.md) | Checklist item a item do que o enunciado cobra, e o que ainda falta |
| [evidencias/](evidencias/README.md) | Validações datadas: comando, saída real e veredito de cada uma |
| [evidencias/prints/](evidencias/prints/README.md) | **Guia dos 13 prints**: como deixar cada tela no estado certo, o que precisa aparecer no quadro e o erro comum de cada um |
| [backlog-pos-entrega.md](backlog-pos-entrega.md) | O que foi visto e **escolhido não fazer** agora, com o motivo |

## 👷 Como o time trabalha

| Documento | Responde |
|---|---|
| [fluxo-git.md](fluxo-git.md) | Branches, commits, PRs, issues, labels e versões |
| [padroes-de-codigo.md](padroes-de-codigo.md) | Convenções de Python, FastAPI, Streamlit e Arduino |
| [definicao-de-pronto.md](definicao-de-pronto.md) | Quando uma task pode começar e quando está pronta |
| [fluxo-agentes.md](fluxo-agentes.md) | Dinâmica de geração de código com os agentes (devs por área + revisor) |

## 🗄 Histórico

| Documento | Responde |
|---|---|
| [plano-de-implementacao.md](plano-de-implementacao.md) | O plano escrito **antes** de implementar, mantido para comparar plano e resultado. Para o estado atual, use o guia |

## Regras de ouro

1. **Nada entra na `main` sem PR.** A `main` precisa estar sempre pronta para a demo.
2. **Mudou o projeto, atualizou o `README.md`**, no mesmo PR.
3. **Regra de risco só existe em um lugar:** na `api/`, seguindo [regras-de-risco.md](regras-de-risco.md). O front e o firmware só exibem ou aplicam o que a API calcula.
4. **Contrato mudou, os dois lados mudam juntos.** Se um tópico ou payload MQTT mudar, atualize `contrato-mqtt.md`, o firmware e a API no mesmo PR.
5. **O código congelou em 25/09** — e o congelamento foi **aberto duas vezes em 27/09**, a pedido
   do grupo: a **W14** (cadastro de maquinário) e a **I7** (execução em Docker). As duas são
   **aditivas** — nenhuma altera comportamento já existente —, entraram com especificação,
   revisão e evidência datada, e as suítes seguiram verdes (`1007` na api, `188` no front-web,
   `pio run` passando). Fora essas duas, só correções de bug que afetam a demo.
