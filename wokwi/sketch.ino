/*
 * AgroCollective - Fleet Node v0.1
 * ESP32 DevKit C V4 — flota de 10 parcelas
 *
 * Sensores físicos:
 *   GPIO 15 → DHT22 (temp aire + humedad relativa)
 *   GPIO  5 → DS18B20 (temp suelo, OneWire)
 *   GPIO 34 → Sensor capacitivo humedad suelo (ADC1_CH6)
 *
 * Cada ciclo (PUBLISH_INTERVAL ms) lee los sensores una vez y publica
 * 10 mensajes MQTT con variaciones por parcela para simular condiciones distintas.
 * El timestamp es simulado: cada ciclo avanza 3 horas (SIM_STEP segundos).
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>

// ── Configuración ──────────────────────────────────────────────────────────────

const char* WIFI_SSID        = "Wokwi-GUEST";
const char* WIFI_PASS        = "";
const char* MQTT_BROKER      = "broker.hivemq.com";
const int   MQTT_PORT        = 1883;
const char* MQTT_CLIENT_ID   = "agrocollective-fleet-001";

const unsigned long PUBLISH_INTERVAL = 10000UL;   // ms entre ciclos
const unsigned long SIM_STEP         = 10800UL;   // segundos simulados por ciclo (3h)

// ── Pines ──────────────────────────────────────────────────────────────────────

#define DHT_PIN  15
#define DHT_TYPE DHT22
#define DS_PIN    5
#define SOIL_PIN 34

// SEN0193: seco ~2800 (ADC 12-bit), mojado ~1200
#define SOIL_DRY_ADC  2800
#define SOIL_WET_ADC  1200

// ── Objetos hardware ────────────────────────────────────────────────────────────

DHT               dht(DHT_PIN, DHT_TYPE);
OneWire           oneWire(DS_PIN);
DallasTemperature ds18b20(&oneWire);
WiFiClient        wifiClient;
PubSubClient      mqtt(wifiClient);

// ── Flota de 10 parcelas ────────────────────────────────────────────────────────

#define FLEET_SIZE 10

struct Parcela {
  const char* finca_id;
  const char* parcela_id;
  const char* esp32_id;
  const char* cultivo;
  const char* region;
  int         depth_cm;
  float       battery_mv;
};

// 4 olivos, 3 almendros, 3 viñas — 5 VALENCIA, 5 BAZA
// esp32_id provisionales; sustituir por los reales tras el seed de la API
Parcela fleet[FLEET_SIZE] = {
  {"F001", "P001", "ESP-P001", "olivo",    "VALENCIA", 30, 4200.0f},
  {"F001", "P002", "ESP-P002", "almendro", "VALENCIA", 30, 4185.0f},
  {"F002", "P001", "ESP-P003", "viña",     "VALENCIA", 30, 4170.0f},
  {"F002", "P002", "ESP-P004", "olivo",    "BAZA",     30, 4155.0f},
  {"F003", "P001", "ESP-P005", "almendro", "BAZA",     30, 4140.0f},
  {"F003", "P002", "ESP-P006", "viña",     "BAZA",     30, 4125.0f},
  {"F004", "P001", "ESP-P007", "olivo",    "VALENCIA", 30, 4110.0f},
  {"F004", "P002", "ESP-P008", "almendro", "BAZA",     30, 4095.0f},
  {"F005", "P001", "ESP-P009", "viña",     "VALENCIA", 30, 4080.0f},
  {"F005", "P002", "ESP-P010", "olivo",    "BAZA",     30, 4065.0f},
};

// ── Tiempo simulado ─────────────────────────────────────────────────────────────
// 2025-05-01 00:00:00 UTC = 1746057600
unsigned long simEpoch  = 1746057600UL;
unsigned long lastPublish = 0;

// ── Funciones auxiliares ────────────────────────────────────────────────────────

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.printf("[WiFi] Conectando a '%s'...\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long t = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t < 15000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WiFi] OK — IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("[WiFi] ERROR: tiempo de espera agotado");
  }
}

void connectMQTT() {
  if (mqtt.connected()) return;
  Serial.printf("[MQTT] Conectando a %s:%d...\n", MQTT_BROKER, MQTT_PORT);
  if (mqtt.connect(MQTT_CLIENT_ID)) {
    Serial.println("[MQTT] Conectado");
  } else {
    Serial.printf("[MQTT] ERROR rc=%d\n", mqtt.state());
  }
}

// Convierte unix epoch a cadena ISO 8601 UTC ("2025-06-01T00:00:00Z")
String epochToISO8601(unsigned long epoch) {
  unsigned long e = epoch;
  int sec  = e % 60; e /= 60;
  int min  = e % 60; e /= 60;
  int hour = e % 24; e /= 24;

  unsigned long days = e;
  int year = 1970;
  while (true) {
    bool leap    = (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0));
    unsigned diy = leap ? 366u : 365u;
    if (days < diy) break;
    days -= diy;
    year++;
  }
  bool leap = (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0));
  int dim[] = {31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
  int month = 0;
  while ((unsigned long)dim[month] <= days) { days -= dim[month]; month++; }

  char buf[25];
  snprintf(buf, sizeof(buf), "%04d-%02d-%02dT%02d:%02d:%02dZ",
           year, month + 1, (int)days + 1, hour, min, sec);
  return String(buf);
}

// Publica las 10 parcelas de la flota en un único ciclo
void publishFleet() {
  // Una sola lectura física — luego se aplica variación por parcela
  ds18b20.requestTemperatures();

  float baseAirTemp  = dht.readTemperature();
  float baseRelHum   = dht.readHumidity();
  float baseSoilTemp = ds18b20.getTempCByIndex(0);
  int   rawSoil      = analogRead(SOIL_PIN);

  // Valores de fallback si el sensor no responde en Wokwi
  if (isnan(baseAirTemp))                        baseAirTemp  = 22.5f;
  if (isnan(baseRelHum))                         baseRelHum   = 62.0f;
  if (baseSoilTemp == DEVICE_DISCONNECTED_C)     baseSoilTemp = 19.5f;

  // ADC 12-bit → humedad suelo %: seco 0% (~2800), mojado 100% (~1200)
  float baseHum = (float)(SOIL_DRY_ADC - rawSoil) /
                  (float)(SOIL_DRY_ADC - SOIL_WET_ADC) * 100.0f;
  baseHum = constrain(baseHum, 0.0f, 100.0f);

  String ts = epochToISO8601(simEpoch);

  for (int i = 0; i < FLEET_SIZE; i++) {
    Parcela& p = fleet[i];

    // Variación determinista por índice (±1.8 °C entre extremos de flota)
    float delta = (i - 4.5f) * 0.4f;

    float airTemp  = baseAirTemp  + delta;
    float soilTemp = baseSoilTemp + delta * 0.6f;
    float relHum   = baseRelHum   - delta * 0.8f;
    float soilHum  = constrain(baseHum + i * 1.5f, 0.0f, 100.0f);

    // Batería: descarga lenta y ligeramente aleatoria
    p.battery_mv -= (float)random(0, 4) / 10.0f;
    if (p.battery_mv < 3300.0f) p.battery_mv = 3300.0f;

    // Tópico
    char topic[80];
    snprintf(topic, sizeof(topic),
             "fincas/%s/parcelas/%s/lecturas", p.finca_id, p.parcela_id);

    // Payload
    StaticJsonDocument<256> doc;
    doc["finca_id"]          = p.finca_id;
    doc["parcela_id"]        = p.parcela_id;
    doc["esp32_id"]          = p.esp32_id;
    doc["timestamp"]         = ts;
    doc["soil_humidity"]     = round(soilHum  * 10.0f) / 10.0f;
    doc["soil_temp"]         = round(soilTemp * 10.0f) / 10.0f;
    doc["air_temp"]          = round(airTemp  * 10.0f) / 10.0f;
    doc["relative_humidity"] = round(relHum   * 10.0f) / 10.0f;
    doc["battery_mv"]        = (int)p.battery_mv;
    doc["depth_cm"]          = p.depth_cm;

    char payload[256];
    serializeJson(doc, payload);

    bool ok = mqtt.publish(topic, payload);
    Serial.printf("[%s/%s] (%s) %s\n",
                  p.finca_id, p.parcela_id, ok ? "OK" : "FAIL", payload);
    delay(50);  // pequeña pausa entre mensajes consecutivos
  }

  simEpoch += SIM_STEP;
  Serial.printf("--- Ciclo completo. Próximo ts: %s ---\n\n",
                epochToISO8601(simEpoch).c_str());
}

// ── Setup / Loop ────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("=== AgroCollective Fleet Node v0.1 ===");
  Serial.printf("Flota: %d parcelas | Intervalo: %lu ms | Paso simulado: %lu s (3h)\n\n",
                FLEET_SIZE, PUBLISH_INTERVAL, SIM_STEP);

  dht.begin();
  ds18b20.begin();

  connectWiFi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  connectMQTT();
}

void loop() {
  connectWiFi();
  connectMQTT();
  mqtt.loop();

  if (millis() - lastPublish >= PUBLISH_INTERVAL) {
    lastPublish = millis();
    publishFleet();
  }
}
