# =============================================================
# FARMTECH SOLUTIONS - Modelo de Decisão de Irrigação
# Cultura: TOMATE
# Método: Regressão Logística (classificação binária)
# =============================================================
if (!require("dplyr")) install.packages("dplyr")
if (!require("ggplot2")) install.packages("ggplot2")
library(dplyr)
library(ggplot2)

set.seed(42)

dados <- data.frame(
  umidade       = c(35, 45, 55, 65, 75, 30, 40, 50, 60, 70,
                    25, 80, 42, 58, 67, 38, 72, 48, 62, 33,
                    55, 48, 70, 36, 62, 44, 78, 52, 39, 66),
  ph            = c(6.5, 6.2, 6.8, 7.0, 6.0, 5.8, 6.4, 6.6, 6.3, 6.7,
                    5.5, 7.2, 6.1, 6.9, 6.4, 5.9, 6.8, 6.5, 6.2, 5.7,
                    6.3, 6.0, 6.6, 5.8, 6.4, 6.1, 6.9, 6.5, 5.9, 6.7),
  npk_count     = c(3, 2, 3, 3, 3, 1, 2, 3, 3, 3,
                    0, 3, 2, 3, 3, 1, 3, 2, 3, 1,
                    2, 1, 3, 1, 3, 2, 3, 2, 1, 3),
  chuva_mm      = c(0, 0, 2, 5, 8, 0, 0, 1, 3, 6,
                    0, 10, 0, 2, 4, 0, 7, 1, 3, 0,
                    1, 0, 5, 0, 3, 0, 8, 2, 0, 6),
  irrigar       = c(1, 1, 1, 0, 0, 1, 1, 1, 0, 0,
                    1, 0, 1, 1, 0, 1, 0, 1, 0, 1,
                    1, 1, 0, 1, 0, 1, 0, 1, 1, 0)
)

# -------------------------------------------------------------
# 2. ANÁLISE EXPLORATÓRIA
# -------------------------------------------------------------
cat("\n=========== RESUMO ESTATÍSTICO ===========\n")
print(summary(dados))

cat("\n=========== CORRELAÇÕES ===========\n")
print(round(cor(dados), 3))

# -------------------------------------------------------------
# 3. MODELO DE REGRESSÃO LOGÍSTICA
# -------------------------------------------------------------
modelo <- glm(
  irrigar ~ umidade + ph + npk_count + chuva_mm,
  data   = dados,
  family = binomial
)

cat("\n=========== MODELO LOGÍSTICO ===========\n")
print(summary(modelo))

# Pseudo R² (McFadden)
null_model <- glm(irrigar ~ 1, data = dados, family = binomial)
pseudoR2 <- 1 - (logLik(modelo) / logLik(null_model))
cat(sprintf("\nPseudo R² (McFadden): %.4f\n", pseudoR2))

# Acurácia no próprio dataset
probs <- predict(modelo, type = "response")
preds <- ifelse(probs > 0.5, 1, 0)
acuracia <- mean(preds == dados$irrigar)
cat(sprintf("Acurácia no treino: %.2f%%\n", acuracia * 100))

# -------------------------------------------------------------
# 4. FUNÇÃO DE DECISÃO
# -------------------------------------------------------------
decidir_irrigacao <- function(umidade, ph, npk, chuva) {
  novo <- data.frame(
    umidade   = umidade,
    ph        = ph,
    npk_count = npk,
    chuva_mm  = chuva
  )
  prob    <- predict(modelo, newdata = novo, type = "response")
  decisao <- ifelse(prob > 0.5, "LIGAR BOMBA", "DESLIGAR BOMBA")

  cat(sprintf("\n--- Cenário ---\n"))
  cat(sprintf("  Umidade=%.1f%% | pH=%.1f | NPK=%d | Chuva=%.1fmm\n",
              umidade, ph, npk, chuva))
  cat(sprintf("  Probabilidade de irrigar: %.2f%%\n", prob * 100))
  cat(sprintf("  >> DECISÃO: %s\n", decisao))
}

# -------------------------------------------------------------
# 5. CENÁRIOS DE TESTE
# -------------------------------------------------------------
cat("\n=========== CENÁRIOS ===========")
decidir_irrigacao(umidade = 40, ph = 6.5, npk = 3, chuva = 0)  # solo seco
decidir_irrigacao(umidade = 70, ph = 6.5, npk = 3, chuva = 8)  # úmido + chuva
decidir_irrigacao(umidade = 55, ph = 5.5, npk = 1, chuva = 0)  # pH ruim + NPK baixo
decidir_irrigacao(umidade = 35, ph = 6.3, npk = 2, chuva = 10) # muito seco + chuvão

# -------------------------------------------------------------
# 6. GRÁFICO DE VISUALIZAÇÃO
# -------------------------------------------------------------
grafico <- ggplot(dados, aes(x = umidade, y = irrigar, color = factor(irrigar))) +
  geom_jitter(width = 0, height = 0.05, size = 3, alpha = 0.8) +
  geom_smooth(aes(group = 1),
              method = "glm",
              method.args = list(family = "binomial"),
              se = TRUE, color = "steelblue") +
  scale_color_manual(values = c("#e74c3c", "#27ae60"),
                     labels = c("Não irrigar", "Irrigar")) +
  labs(
    title    = "FarmTech Solutions - Probabilidade de Irrigação",
    subtitle = "Regressão logística: Umidade vs Decisão",
    x = "Umidade do Solo (%)",
    y = "Decisão (0 = Não irrigar, 1 = Irrigar)",
    color = "Ação"
  ) +
  theme_minimal(base_size = 12)

print(grafico)
ggsave("analise_r/grafico_decisao.png", grafico, width = 9, height = 5, dpi = 150)

cat("\n\n>> Análise concluída!\n")
cat(">> Gráfico salvo em: analise_r/grafico_decisao.png\n")