#include <Arduino.h>
#include <DHT.h>
#include <WiFi.h>
#include <HTTPClient.h>

#define DHT_PIN 15
#define DHT_TYPE DHT22

#define SOIL_MOISTURE_PIN 32
#define PH_PIN 33
#define NITROGEN_PIN 35
#define PHOSPHORUS_PIN 25
#define POTASSIUM_PIN 26
#define LDR_PIN 34

#define COLLECTION_INTERVAL_MS 5000

const char* serverUrl = "http://host.wokwi.internal:8000/soil";

DHT dht(DHT_PIN, DHT_TYPE);

struct SoilData {
  float airHumidity;
  float airTemperature;
  int soilMoistureRaw;
  int soilMoisturePercent;
  float ph;
  int nitrogen;
  int phosphorus;
  int potassium;
  int lightRaw;
  float lightPercent;
};

SoilData data;

void connectWiFi() {
  WiFi.begin("Wokwi-GUEST", "", 6);
  while (WiFi.status() != WL_CONNECTED) {
    delay(100);
    Serial.print(".");
  }
  Serial.println(" Connected!");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(9600);

  dht.begin();

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);

  pinMode(SOIL_MOISTURE_PIN, INPUT);
  pinMode(PH_PIN, INPUT);
  pinMode(NITROGEN_PIN, INPUT);
  pinMode(PHOSPHORUS_PIN, INPUT);
  pinMode(POTASSIUM_PIN, INPUT);
  pinMode(LDR_PIN, INPUT);

  connectWiFi();

  Serial.println(F("=== ESP32 Soil Data Collector started ==="));
  Serial.print(F("Collection interval: "));
  Serial.print(COLLECTION_INTERVAL_MS / 1000);
  Serial.println(F(" seconds"));
}

int readAnalogPercent(int pin) {
  int raw = analogRead(pin);
  return constrain(map(raw, 0, 4095, 0, 100), 0, 100);
}

void readSensors() {
  data.airHumidity = dht.readHumidity();
  data.airTemperature = dht.readTemperature();

  if (isnan(data.airHumidity)) data.airHumidity = -1;
  if (isnan(data.airTemperature)) data.airTemperature = -1;

  data.soilMoistureRaw = analogRead(SOIL_MOISTURE_PIN);
  data.soilMoisturePercent = constrain(map(data.soilMoistureRaw, 0, 4095, 100, 0), 0, 100);

  int phRaw = analogRead(PH_PIN);
  data.ph = map(phRaw, 0, 4095, 0, 1400) / 100.0f;

  data.nitrogen = readAnalogPercent(NITROGEN_PIN);
  data.phosphorus = readAnalogPercent(PHOSPHORUS_PIN);
  data.potassium = readAnalogPercent(POTASSIUM_PIN);

  data.lightRaw = analogRead(LDR_PIN);
  data.lightPercent = data.lightRaw / 4095.0f * 100.0f;
}

void printData() {
  Serial.println(F("--- Soil Data Collection ---"));
  Serial.print(F("Timestamp (ms): "));
  Serial.println(millis());

  Serial.print(F("Air Humidity: "));
  Serial.print(data.airHumidity);
  Serial.println(F(" %"));

  Serial.print(F("Air Temperature: "));
  Serial.print(data.airTemperature);
  Serial.println(F(" C"));

  Serial.print(F("Soil Moisture: "));
  Serial.print(data.soilMoisturePercent);
  Serial.print(F(" % (raw: "));
  Serial.print(data.soilMoistureRaw);
  Serial.println(F(")"));

  Serial.print(F("Soil pH: "));
  Serial.println(data.ph, 2);

  Serial.print(F("Nitrogen (N): "));
  Serial.print(data.nitrogen);
  Serial.println(F(" %"));

  Serial.print(F("Phosphorus (P): "));
  Serial.print(data.phosphorus);
  Serial.println(F(" %"));

  Serial.print(F("Potassium (K): "));
  Serial.print(data.potassium);
  Serial.println(F(" %"));

  Serial.print(F("Luminosity: "));
  Serial.print(data.lightPercent, 1);
  Serial.print(F(" % (raw: "));
  Serial.print(data.lightRaw);
  Serial.println(F(")"));

  Serial.println(F("----------------------------\n"));
}

void sendData() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("Wi-Fi not connected, skipping POST"));
    return;
  }

  HTTPClient http;
  Serial.println(serverUrl);
  http.begin(serverUrl);
  http.addHeader(F("Content-Type"), F("application/json"));

  String payload = "{";
  payload += "\"air_humidity\":" + String(data.airHumidity, 2) + ",";
  payload += "\"air_temperature\":" + String(data.airTemperature, 2) + ",";
  payload += "\"soil_moisture_raw\":" + String(data.soilMoistureRaw) + ",";
  payload += "\"soil_moisture_percent\":" + String(data.soilMoisturePercent) + ",";
  payload += "\"ph\":" + String(data.ph, 2) + ",";
  payload += "\"nitrogen\":" + String(data.nitrogen) + ",";
  payload += "\"phosphorus\":" + String(data.phosphorus) + ",";
  payload += "\"potassium\":" + String(data.potassium) + ",";
  payload += "\"light_raw\":" + String(data.lightRaw) + ",";
  payload += "\"light_percent\":" + String(data.lightPercent, 2);
  payload += "}";

  int httpCode = http.POST(payload);
  Serial.print(F("HTTP POST code: "));
  Serial.println(httpCode);
  if (httpCode > 0) {
    Serial.println(http.getString());
  } else {
    Serial.print(F("HTTP error: "));
    Serial.println(http.errorToString(httpCode));
  }
  http.end();
}

void loop() {
  readSensors();
  printData();
  sendData();
  delay(COLLECTION_INTERVAL_MS);
}
