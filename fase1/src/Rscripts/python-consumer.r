
# Leitura do arquivo CSV (execute a partir de fase1/src: Rscript Rscripts/python-consumer.r)
dados <- read.csv("farm_tech_solutions.csv", sep = ";", header = TRUE)

cat("============================================================\n")
cat("       SISTEMA DE ANÁLISE ESTATÍSTICA AGRÍCOLA\n")
cat("============================================================\n\n")

# Visualização dos dados carregados
cat(">>> DADOS CARREGADOS:\n")
print(dados)
cat("\n")


dados_manga <- subset(dados, type == "Manga")
dados_cana  <- subset(dados, type == "Cana")

calcular_estatisticas <- function(valores, nome_var, unidade) {
  if (length(valores) == 0 || all(is.na(valores))) {
    cat("  Sem dados suficientes para", nome_var, "\n")
    return(invisible(NULL))
  }

  media   <- mean(valores, na.rm = TRUE)
  desvio  <- ifelse(length(valores) > 1, sd(valores, na.rm = TRUE), 0)
  minimo  <- min(valores, na.rm = TRUE)
  maximo  <- max(valores, na.rm = TRUE)
  mediana <- median(valores, na.rm = TRUE)
  n       <- length(valores)

  cat(sprintf("  Variável  : %s (%s)\n", nome_var, unidade))
  cat(sprintf("  N         : %d registro(s)\n", n))
  cat(sprintf("  Média     : %.4f %s\n", media, unidade))
  cat(sprintf("  Desvio P. : %.4f %s\n", desvio, unidade))
  cat(sprintf("  Mediana   : %.4f %s\n", mediana, unidade))
  cat(sprintf("  Mínimo    : %.4f %s\n", minimo, unidade))
  cat(sprintf("  Máximo    : %.4f %s\n\n", maximo, unidade))
}

# ============================================================
# ESTATÍSTICAS - MANGA
# ============================================================
cat("============================================================\n")
cat("  🥭 MANGA\n")
cat("============================================================\n\n")

cat("--- Área de Plantio ---\n")
calcular_estatisticas(dados_manga$area, "Área", "m²")

cat("--- Manejo de Insumos ---\n")
cat("  ⚠️  Unidade: LITROS (L) — pulverização líquida\n\n")
calcular_estatisticas(dados_manga$input_management, "Insumo", "L")

# ============================================================
# ESTATÍSTICAS - CANA-DE-AÇÚCAR
# ============================================================
cat("============================================================\n")
cat("  🌾 CANA-DE-AÇÚCAR\n")
cat("============================================================\n\n")

cat("--- Área de Plantio ---\n")
calcular_estatisticas(dados_cana$area, "Área", "m²")

cat("--- Manejo de Insumos ---\n")
cat("  ⚠️  Unidade: QUILOGRAMAS (kg) — aplicação sólida\n\n")
calcular_estatisticas(dados_cana$input_management, "Insumo", "kg")

# ============================================================
# COMPARATIVO GERAL - ÁREA
# ============================================================
cat("============================================================\n")
cat("  📊 COMPARATIVO GERAL — ÁREA (m²)\n")
cat("============================================================\n")
cat(sprintf("  Média Manga : %.4f m²\n", mean(dados_manga$area, na.rm = TRUE)))
cat(sprintf("  Média Cana  : %.4f m²\n", mean(dados_cana$area,  na.rm = TRUE)))
cat(sprintf("  Média Geral : %.4f m²\n", mean(dados$area,       na.rm = TRUE)))
cat(sprintf("  Desvio Geral: %.4f m²\n\n", sd(dados$area,       na.rm = TRUE)))

cat("============================================================\n")
cat("  ✅ Análise concluída!\n")
cat("============================================================\n")