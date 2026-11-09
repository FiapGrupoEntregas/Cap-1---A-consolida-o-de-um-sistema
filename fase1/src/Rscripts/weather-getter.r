install.packages("httr")
install.packages("jsonlite")

library(httr)
library(jsonlite)


city <- "São Paulo"
latitude <- -23.5505
longitude <- -46.6333

get_weather <- function(lat, lon) {
  url <- "https://api.open-meteo.com/v1/forecast"

  params <- list(
    latitude = lat,
    longitude = lon,
    current = paste(c(
      "temperature_2m",
      "relative_humidity_2m",
      "apparent_temperature",
      "precipitation",
      "wind_speed_10m",
      "wind_direction_10m",
      "weather_code",
      "cloud_cover"
    ), collapse = ","),
    daily = paste(c(
      "temperature_2m_max",
      "temperature_2m_min",
      "precipitation_sum",
      "weather_code"
    ), collapse = ","),
    timezone = "America/Sao_Paulo",
    forecast_days = 5
  )

  response <- GET(url, query = params)

  if (status_code(response) != 200) {
    stop("Erro ao conectar à API: ", status_code(response))
  }

  fromJSON(content(response, as = "text", encoding = "UTF-8"))
}

decode_weather_code <- function(code) {
  codes <- c(
    "0"  = "Céu limpo",
    "1"  = "Principalmente limpo",
    "2"  = "Parcialmente nublado",
    "3"  = "Nublado",
    "45" = "Névoa",
    "48" = "Névoa com geada",
    "51" = "Garoa leve",
    "53" = "Garoa moderada",
    "55" = "Garoa intensa",
    "61" = "Chuva leve",
    "63" = "Chuva moderada",
    "65" = "Chuva forte",
    "71" = "Neve leve",
    "73" = "Neve moderada",
    "75" = "Neve forte",
    "80" = "Pancadas leves",
    "81" = "Pancadas moderadas",
    "82" = "Pancadas fortes",
    "95" = "Tempestade",
    "96" = "Tempestade com granizo",
    "99" = "Tempestade severa com granizo"
  )
  label <- codes[as.character(code)]
  if (is.na(label)) return(paste("Código:", code))
  label
}

# ── Função: direção do vento em texto ───────────────────────
wind_direction_label <- function(deg) {
  dirs <- c("N","NNE","NE","ENE","E","ESE","SE","SSE",
            "S","SSO","SO","OSO","O","ONO","NO","NNO")
  idx <- round(deg / 22.5) %% 16 + 1
  dirs[idx]
}

# ── Função: exibir relatório no terminal ────────────────────
print_weather_report <- function(data, city) {
  cur   <- data$current
  daily <- data$daily

  sep <- paste(rep("─", 50), collapse = "")

  cat("\n")
  cat(sep, "\n")
  cat(sprintf("    PREVISÃO DO TEMPO — %s\n", toupper(city)))
  cat(sep, "\n")

  # Condições atuais
  cat("\nCONDIÇÕES ATUAIS\n")
  cat(sprintf("  Atualizado em  : %s\n", cur$time))
  cat(sprintf("  Condição       : %s\n", decode_weather_code(cur$weather_code)))
  cat(sprintf("  Temperatura    : %.1f°C  (sensação: %.1f°C)\n",
              cur$temperature_2m, cur$apparent_temperature))
  cat(sprintf("  Umidade        : %d%%\n", cur$relative_humidity_2m))
  cat(sprintf("  Precipitação   : %.1f mm\n", cur$precipitation))
  cat(sprintf("  Nebulosidade   : %d%%\n", cur$cloud_cover))
  cat(sprintf("  Vento          : %.1f km/h — %s (%d°)\n",
              cur$wind_speed_10m,
              wind_direction_label(cur$wind_direction_10m),
              cur$wind_direction_10m))

  # Previsão dos próximos dias
  cat("\n📅 PREVISÃO — PRÓXIMOS 5 DIAS\n")
  cat(sprintf("  %-12s %-28s %6s %6s %8s\n",
              "Data", "Condição", "Máx", "Mín", "Chuva"))
  cat(sprintf("  %s\n", paste(rep("-", 64), collapse = "")))

  for (i in seq_along(daily$time)) {
    cat(sprintf("  %-12s %-28s %5.1f° %5.1f° %6.1f mm\n",
                daily$time[i],
                decode_weather_code(daily$weather_code[i]),
                daily$temperature_2m_max[i],
                daily$temperature_2m_min[i],
                daily$precipitation_sum[i]))
  }

  cat("\n", sep, "\n")
  cat("  Fonte: Open-Meteo (https://open-meteo.com)\n")
  cat(sep, "\n\n")
}

cat("Buscando dados meteorológicos para", city, "...\n")

tryCatch({
  dados <- get_weather(latitude, longitude)
  print_weather_report(dados, city)
}, error = function(e) {
  cat("Erro:", conditionMessage(e), "\n")
})