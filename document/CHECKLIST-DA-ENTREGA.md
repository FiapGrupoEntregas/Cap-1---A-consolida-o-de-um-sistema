# O que falta entregar — checklist do Challenge Sompo, Sprint 4

> Este documento responde uma pergunta só: **o que ainda preciso fazer para entregar?**
> Cada linha tem o que o enunciado pede, se está pronto e a ação exata.
>
> O status feature a feature fica em [`feature/README.md`](../feature/README.md), e a análise
> detalhada de cada entregável em [entregaveis.md](entregaveis.md). Aqui é só a lista de ações.
>
> Conferido em **28/09/2026**.

---

## 🔴 Primeiro: a branch padrão do repositório está desatualizada

Tudo **está enviado** — a branch `chore/estrutura-inicial` no GitHub está idêntica à local.

O problema é outro: a **branch padrão do repositório é a `main`**, e ela está **29 commits atrás**.
Quem abrir o repositório vê a `main` por padrão — e nela **não existem** os prints, o Docker, o
link do vídeo, o esquema do banco nem o diagrama de arquitetura.

Duas saídas, qualquer uma resolve:

```bash
# A) trazer o trabalho para a main (recomendado)
git checkout main && git merge chore/estrutura-inicial && git push origin main

# B) ou mudar a branch padrão no GitHub:
#    Settings → General → Default branch → chore/estrutura-inicial
```

A opção A é a convencional e a que menos surpreende quem corrige.

## Os 9 entregáveis do enunciado

| # | Entregável | Situação | O que fazer |
|---|---|---|---|
| 1 | Sistema consolidado, modular, com exceções tratadas e fluxo reproduzível | ✅ | Nada — 1.007 testes na API, 188 no front, e `docker compose up` sobe tudo |
| 2 | Banco e modelo final, com métricas e justificativa | ✅ | Nada — artefato versionado e método em [dados-e-modelo.md](dados-e-modelo.md) |
| 3 | Validação da integração (confiabilidade da coleta) | ✅ | Nada — testes ponta a ponta e evidências datadas em [evidencias/](evidencias/) |
| 4 | Segurança e rastreabilidade (acesso, proteção, logs) | ✅ | Nada — chave de API, log estruturado e trilha de decisões |
| 5 | Relatórios e interface, com prints | ✅ | 14 prints cobrindo scores, as três tendências e os alertas — ver a nota abaixo |
| 6 | Diagrama de arquitetura final (entrada → banco → modelo → saída) | ✅ | Nada — está em [arquitetura.md](arquitetura.md#diagrama-final-entrada--banco--modelo--saída) |
| 7 | Vídeo de até 5 min, narração humana, YouTube não listado | ✅ | Pronto: https://youtu.be/5-dttjN-_oI |
| 8 | README final com evolução das 4 sprints e link do vídeo | ✅ | Pronto: as quatro sprints escritas e o link publicado |
| 9 | Repositório privado compartilhado com `fiap-tutoria` | ✅ | Privado, e o `fiap-tutoria` já está na organização |

---

## O que ainda falta

**Uma coisa:** atualizar a branch padrão (acima). O resto está entregue.

## Sobre os prints: o que o enunciado pede já está coberto

O enunciado pede, no entregável 5:

> *"**prints ou demonstração** dos relatórios e do dashboard exibindo **scores**, **tendências de
> risco por equipamento, região ou tipo de operação**, e os **alertas e recomendações** gerados."*

Os 14 prints capturados cobrem os três itens:

| O que o enunciado pede | Onde está |
|---|---|
| **scores** | `subscricao--sitio-cafe.png` (classe A/B/C, score 0–100) e o cartão do modelo em `mapa-risco-previsao-de-risco.png` |
| **tendências** por equipamento, região e cultura | `relatorios-equipamentos`, `relatorios-regiao`, `relatorios-cultura` e `relatorio-fazenda-sitio-cafe` |
| **alertas e recomendações** | `mapa-risco-previsao-de-risco.png`, com os motivos em números, e `equipamento-live.png` |

E há mais: relevo, maquinário e replay. **Além disso, o enunciado aceita "prints _ou_
demonstração"** — e o vídeo demonstra o MVP de ponta a ponta.

### A lista dos 13 é um padrão interno, não o requisito

A tabela de controle em [evidencias/prints/README.md](evidencias/prints/README.md) tem 13 itens
porque foi escrita como **meta de qualidade** do projeto, não como cópia do enunciado. Os itens que
faltam ali são **melhorias**, não pendências:

- **item 11** — o cartão do modelo aparece cortado no print atual. É o único que eu ainda
  capturaria, porque a matéria é IA e a ressalva do modelo fica de fora do quadro;
- **itens 6 e 7** — capotamento e alerta local no Wokwi. Enriquecem, e o vídeo já os mostra;
- **itens 3, 4, 5, 8 e 13** — contraste entre fazendas, confirmação de envio, gráfico cheio,
  auditoria e recusa explicada. Todos bons de ter; nenhum exigido.

## O que já está pronto e você não precisa tocar

Para não gastar tempo com o que já foi feito:

- **Código**: API modular em quatro camadas, front sem regra de negócio, firmware completo;
  1.007 + 188 testes, todos offline.
- **Dados e modelo**: 1.525.473 apólices reais carregadas, dataset de 2.256 linhas, modelo
  treinado com divisão temporal, métricas e intervalo de confiança publicados.
- **Segurança**: chave de API com falha fechada, log estruturado com `request_id`, trilha de
  decisões com versão de regra e de modelo, hash SHA-256 de cada evento.
- **Documentação**: README de entrega, guia do projeto, 15 ADRs, user stories com matriz de
  rastreabilidade, evidências datadas e o documento Word com os prints.
- **Execução**: `docker compose up --build` sobe API, front e banco sem instalar nada.
- **Entrega**: vídeo publicado, as quatro sprints escritas no README, documento Word com os
  prints e o diagrama consolidado.

---

## Duas coisas que valem saber antes de entregar

**O repositório será público para a Sompo.** O enunciado diz que a empresa pode incorporar a
ideia. Se o grupo **não** quiser concorrer ao prêmio e preferir sigilo, isso precisa estar
declarado **na primeira capa** — hoje não está. É uma decisão do grupo, não um esquecimento.

**Duas features entraram depois do congelamento de 25/09** (cadastro de maquinário e execução em
Docker). Isso está declarado em [entregaveis.md](entregaveis.md) e no
[índice da documentação](README.md), com o motivo — declarado é melhor que descoberto.
