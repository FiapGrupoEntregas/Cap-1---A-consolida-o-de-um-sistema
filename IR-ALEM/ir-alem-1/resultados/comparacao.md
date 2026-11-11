# Comparação: Amazon Rekognition × YOLOv5 da Fase 6

Gerado em 10/11/2026 00:52 por `rekognition.py --comparar`. A classe verdadeira vem do nome do
arquivo (`vaca_*.jpg`, `trator_*.jpg`); fotos com outro nome ficam sem verdade e não entram na acurácia.

| Imagem | Verdade | Rekognition (rótulo equivalente) | Rekognition: 5 rótulos mais confiantes | Caixas Rekognition | YOLO Fase 6 (classe, confiança) |
|---|---|---|---|---|---|
| `trator_01.jpg` | trator | trator (90%) | Soil 100%, Wheel 99%, Outdoors 94%, Person 94%, Nature 93% | 15 | trator (61%) |
| `trator_02.jpg` | trator | trator (81%) | Wheel 97%, Adult 86%, Male 86%, Man 86%, Person 86% | 7 | trator (74%) |
| `vaca_01.jpg` | vaca | vaca (100%) | Field 100%, Grassland 100%, Nature 100%, Outdoors 100%, Countryside 100% | 1 | vaca (60%) |
| `vaca_02.jpg` | vaca | vaca (100%) | Animal 100%, Cattle 100%, Cow 100%, Dairy Cow 100%, Livestock 100% | 1 | vaca (84%) |

- **Rekognition:** 4 de 4 classes corretas.
- **YOLO da Fase 6:** 4 de 4 classes corretas.

## Leitura

- O Rekognition é um modelo **genérico, pronto**, sem treino: devolve dezenas de rótulos hierárquicos
  (ex.: *Animal → Mammal → Cattle → Cow*) e caixas só para alguns rótulos comuns. Não existe a classe
  "trator" exatamente como na Fase 6; a tabela usa rótulos equivalentes (`EQUIVALENCIAS` no script).
- O YOLO da Fase 6 é **especializado** nas duas classes da fazenda: aprende o que *nós* definimos como
  trator e vaca, roda offline e sem custo por imagem, mas foi treinado com 32 fotos por classe e erra em
  fotos muito diferentes do dataset.
- **Custo e operação:** Rekognition cobra US$ 0,001 por imagem e exige internet e credenciais; o YOLO
  exige manter o modelo, o dataset e o ambiente (PyTorch).
- **Quando usar cada um:** Rekognition para detectar *muitas* coisas sem treinar (pessoas, veículos,
  animais, cenas) e para começar rápido; YOLO próprio quando as classes são específicas do negócio
  (uma praga, um implemento, um defeito) ou quando a inferência precisa rodar na borda (ESP32-CAM, drone).
- **Na FarmTech:** o serviço de alerta pode consumir qualquer um dos dois; o `alerta.py --yolo` lê o JSON
  do `detect.py`, e bastaria mapear os rótulos do Rekognition para o mesmo `resumo` {vaca, trator}.