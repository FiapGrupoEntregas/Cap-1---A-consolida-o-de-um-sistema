#include <Arduino.h>
#include <DHT.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
// =============================================
//  FARMTECH SOLUTIONS - Sistema de Irrigação
//  Cultura de referência: TOMATE
//
//  LÓGICA DE IRRIGAÇÃO:
//  - Umidade ideal tomate: >= 60%
//  - pH ideal tomate: 6.0 a 6.8
//  - NPK: todos presentes idealmente
//
//  LIGA bomba se:
//    1. Umidade < 60% (solo seco)
//    2. OU pH fora de 6.0–6.8 E NPK incompleto
// =============================================

// ===== PINOS =====
#define DHT_PIN       15
#define LDR_PIN       34
#define BTN_N_PIN     12
#define BTN_P_PIN     13
#define BTN_K_PIN     14
#define RELE_BOMBA    27

#define DHT_TYPE      DHT22
#define UMIDADE_MIN   60.0
#define PH_MIN        6.0
#define PH_MAX        6.8
#define LDR_MAX       4095.0

LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(DHT_PIN, DHT_TYPE);

bool nitrogenio, fosforo, potassio;
float umidade = 0.0;
float phSolo  = 0.0;
bool bombaLigada = false;

// Estado climático (atualizado via Serial)
// 'S' = Seco | 'L' = Chuva leve | 'C' = Chuva forte
char climaAtual = 'S';

int telaAtual = 0;
unsigned long ultimaTrocaTela = 0;
const unsigned long INTERVALO_TELA = 2500;


float lerPH() {
  return (analogRead(LDR_PIN) / LDR_MAX) * 14.0;
}

void lerNPK() {
  nitrogenio = (digitalRead(BTN_N_PIN) == LOW);
  fosforo    = (digitalRead(BTN_P_PIN) == LOW);
  potassio   = (digitalRead(BTN_K_PIN) == LOW);
}

// ============================================
//  LEITURA SERIAL (clima vindo do Python)
// ============================================
void verificarClimaSerial() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    c = toupper(c);

    if (c == 'S' || c == 'L' || c == 'C') {
      climaAtual = c;
      Serial.print(">> Clima atualizado via Python: ");
      switch (climaAtual) {
        case 'S': Serial.println("SECO"); break;
        case 'L': Serial.println("CHUVA LEVE"); break;
        case 'C': Serial.println("CHUVA FORTE"); break;
      }
    }
  }
}

bool deveIrrigar() {
  // Chuva forte SEMPRE suspende irrigação
  if (climaAtual == 'C') return false;

  bool soloSeco    = (umidade < UMIDADE_MIN);
  bool phIdeal     = (phSolo >= PH_MIN && phSolo <= PH_MAX);
  bool npkCompleto = (nitrogenio && fosforo && potassio);

  // Chuva leve só irriga se solo muito seco (< 40%)
  if (climaAtual == 'L') {
    return (umidade < 40.0);
  }

  // Seco verifica comportamentos
  if (soloSeco) return true;
  if (!phIdeal && !npkCompleto) return true;

  return false;
}

// ============================================
//  TELAS LCD
// ============================================
void telaUmidadePH() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Umid:");
  lcd.print(umidade, 1);
  lcd.print("%");

  lcd.setCursor(0, 1);
  lcd.print("pH:");
  lcd.print(phSolo, 1);
  lcd.print((phSolo >= PH_MIN && phSolo <= PH_MAX) ? " IDEAL" : " FORA");
}

void telaNPK() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Nutrientes NPK");
  lcd.setCursor(0, 1);
  lcd.print("N:");  lcd.print(nitrogenio ? "ON " : "OFF");
  lcd.print(" P:"); lcd.print(fosforo    ? "ON" : "OFF");
  lcd.print(" K:"); lcd.print(potassio   ? "ON" : "OFF");
}

void telaClima() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Clima (API):");
  lcd.setCursor(0, 1);
  switch (climaAtual) {
    case 'S': lcd.print("SECO");        break;
    case 'L': lcd.print("CHUVA LEVE");  break;
    case 'C': lcd.print("CHUVA FORTE"); break;
  }
}

void telaBomba() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Bomba d'agua:");
  lcd.setCursor(0, 1);
  lcd.print(bombaLigada ? ">> LIGADA <<" : ">> DESLIGADA");
}

void atualizarLCD() {
  if (millis() - ultimaTrocaTela >= INTERVALO_TELA) {
    ultimaTrocaTela = millis();
    telaAtual = (telaAtual + 1) % 4;
    switch (telaAtual) {
      case 0: telaUmidadePH(); break;
      case 1: telaNPK();       break;
      case 2: telaClima();     break;
      case 3: telaBomba();     break;
    }
  }
}

void exibirSerial() {
  Serial.println("================================================");
  Serial.println("  FARMTECH - Monitor Agrícola");
  Serial.println("================================================");
  Serial.print("  Umidade: "); Serial.print(umidade, 1); Serial.println(" %");
  Serial.print("  pH:      "); Serial.println(phSolo, 2);
  Serial.print("  N: "); Serial.print(nitrogenio ? "ON" : "OFF");
  Serial.print(" | P: "); Serial.print(fosforo ? "ON" : "OFF");
  Serial.print(" | K: "); Serial.println(potassio ? "ON" : "OFF");
  Serial.print("  Clima:   ");
  
  switch (climaAtual) {
    case 'S': Serial.println("SECO");        break;
    case 'L': Serial.println("CHUVA LEVE");  break;
    case 'C': Serial.println("CHUVA FORTE"); break;
  }
  Serial.print("  BOMBA:   ");
  Serial.println(bombaLigada ? "LIGADA 💧" : "DESLIGADA");
  Serial.println("  (Digite S/L/C + Enter para atualizar clima)");
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  dht.begin();

  pinMode(BTN_N_PIN, INPUT_PULLUP);
  pinMode(BTN_P_PIN, INPUT_PULLUP);
  pinMode(BTN_K_PIN, INPUT_PULLUP);
  pinMode(RELE_BOMBA, OUTPUT);
  digitalWrite(RELE_BOMBA, LOW);

  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.print("FarmTech");
  lcd.setCursor(0, 1);
  lcd.print("Solutions");
  delay(1500);

  Serial.println("\n>> FarmTech iniciado!");
  Serial.println(">> Digite S/L/C no Serial para simular clima");
  Serial.println("   (S=Seco, L=Chuva Leve, C=Chuva Forte)\n");
}

void loop() {
  umidade = dht.readHumidity();
  phSolo  = lerPH();
  lerNPK();
  verificarClimaSerial();

  if (isnan(umidade)) {
    Serial.println(">> Erro DHT22");
    delay(1000);
    return;
  }

  bombaLigada = deveIrrigar();
  digitalWrite(RELE_BOMBA, bombaLigada ? HIGH : LOW);

  atualizarLCD();

  static unsigned long ultimoSerial = 0;
  if (millis() - ultimoSerial >= 3000) {
    ultimoSerial = millis();
    exibirSerial();
  }

  delay(100);
}