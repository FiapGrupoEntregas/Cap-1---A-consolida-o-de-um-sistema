# 05 — Documentação, vídeo e entrega

**Critérios:** 1, 2, 4 e 7 (3 pts + 1 extra) · **Depende de:** [01](01-fase6-deteccao.md) a [04](04-alerta-aws.md) · **Situação:** 🟨

## README da raiz

- [ ] Integrantes com **nome completo** e RM. Os nomes atuais estão abreviados ("Natanael Filho",
      "Pedro Henrique"…) e a lista mudou de fase para fase: confirmar quem é o grupo da Fase 7.
- [x] Tabela de status atualizada no fim.
- [x] Seção "Serviço de alertas na AWS" com os prints comentados ([04](04-alerta-aws.md)).
- [x] Arquitetura final (sem linhas tracejadas de "em construção").
- [ ] "Como executar" centrado no `main.py` e na dashboard; testar tudo num clone novo.
- [x] Link do vídeo.

## Roteiro do vídeo (até 10 min)

| Tempo | Conteúdo |
|---|---|
| 0:00–0:45 | O problema e o sistema: as fases viram um sistema só; estrutura do repositório |
| 0:45–1:45 | Dashboard central: visão geral e estado dos serviços |
| 1:45–2:45 | Fase 1: cálculo de área e insumos pelo botão e estatística em R |
| 2:45–3:45 | Fase 2: ESP32 de irrigação no Wokwi e código do clima |
| 3:45–4:45 | Fase 3: consultas no Oracle e dashboard da Fase 3 |
| 4:45–5:45 | Fase 4: ESP32 enviando leituras, API, análise de solo e previsão |
| 5:45–6:45 | Fase 6: imagem enviada e detecção de trator e vaca |
| 6:45–8:45 | Alerta: leitura fora do limite → SNS → e-mail chegando; console da AWS |
| 8:45–9:30 | Fechamento: como o sistema se adapta a outros setores trocando os dados |

- [x] Gravar com voz ou legenda; publicar no YouTube como **não listado**.

## Entrega no portal

- [ ] Abrir um pull request de `feature/entrega-cap-1-fase7` para `main` e integrar.
- [ ] Repositório **privado**, com `fiap-tutoria` adicionado como colaborador (Settings →
      Collaborators → Add people).
- [ ] Arquivo `.txt` com:
  ```
  Repositório: https://github.com/FiapGrupoEntregas/Cap-1---A-consolida-o-de-um-sistema
  Vídeo: <link do YouTube>
  ```
  (mais os links dos vídeos do Ir Além, se houver).
- [ ] Enviar antes do prazo e **não fazer commits depois do envio** (critério 1).
