/*
 * AgroCollective - Fleet Node v0.2
 * ESP32 DevKit C V4 — flota de 10 parcelas
 *
 * Sensores físicos:
 *   GPIO 15 → DHT22  (temperatura aire + humedad relativa)
 *   GPIO  5 → DS18B20 (temperatura suelo, OneWire)
 *   GPIO 34 → Sensor capacitivo humedad suelo (ADC1_CH6)
 *
 * Arquitectura de buffer:
 *   Cada SAMPLE_INTERVAL ms se toman lecturas de los 3 sensores y se
 *   almacenan en sus respectivos buffers.  Cuando los buffers se llenan
 *   (BUFFER_SIZE muestras ≈ 15 min) se aplica preprocesamiento:
 *     1. Se descartan valores nulos o fuera del rango normal de cada sensor.
 *     2. Se calcula la media de los valores válidos restantes.
 *   Con las medias se publica un ciclo completo para las 10 parcelas de la
 *   flota y se reinician los buffers.
 *
 * Tópico de publicación:
 *   fincas/{finca_id}/parcelas/{parcela_id}/lecturas
 *
 * Variables de conexión (declaradas al inicio; no tienen por qué existir
 * en el entorno real — el sketch puede sustituirse por credenciales reales):
 *   WIFI_SSID / WIFI_PASS
 *   MQTT_BROKER / MQTT_PORT / MQTT_CLIENT_ID
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>

// ── Variables de conexión ──────────────────────────────────────────────────────
// Sustituir por credenciales reales; no tienen por qué existir en este entorno.

const char* WIFI_SSID      = "Wokwi-GUEST";
const char* WIFI_PASS      = "";
const char* MQTT_BROKER    = "broker.hivemq.com";
const int   MQTT_PORT      = 1883;
const char* MQTT_CLIENT_ID = "agrocollective-fleet-001";
const char* MQTT_USER      = "";   // dejar vacío si no hay autenticación
const char* MQTT_PASS_STR  = "";   // dejar vacío si no hay autenticación

// ── Pines ──────────────────────────────────────────────────────────────────────

#define DHT_PIN  15
#define DHT_TYPE DHT22
#define DS_PIN    5
#define SOIL_PIN 34

// SEN0193: seco ~2800 (ADC 12-bit), mojado ~1200
#define SOIL_DRY_ADC  2800
#define SOIL_WET_ADC  1200

// ── Configuración de buffer ────────────────────────────────────────────────────

#define BUFFER_SIZE     15          // muestras por ventana (≈ 15 min)
#define SAMPLE_INTERVAL 60000UL    // ms entre muestras (1 minuto)

// Rangos válidos para filtrado de outliers/nulos
#define AIR_TEMP_MIN   -10.0f
#define AIR_TEMP_MAX    60.0f
#define SOIL_TEMP_MIN   -5.0f
#define SOIL_TEMP_MAX   50.0f
#define REL_HUM_MIN      0.0f
#define REL_HUM_MAX    100.0f
#define SOIL_HUM_MIN     0.0f
#define SOIL_HUM_MAX   100.0f

// ── Buffers (3 grupos por sensor físico) ──────────────────────────────────────
// Buffer 1: sensor de temperatura ambiente (DHT22 — temperatura)
float bufAirTemp[BUFFER_SIZE];
int   bufAirTempCount = 0;

// Buffer 2: sensor de temperatura del suelo (DS18B20)
float bufSoilTemp[BUFFER_SIZE];
int   bufSoilTempCount = 0;

// Buffer 3: sensores de humedad — ambiente (DHT22) y suelo (SEN0193)
float bufRelHum [BUFFER_SIZE];
float bufSoilHum[BUFFER_SIZE];
int   bufHumCount = 0;

// ── Objetos hardware ──────────────────────────────────────────────────────────

DHT               dht(DHT_PIN, DHT_TYPE);
OneWire           oneWire(DS_PIN);
DallasTemperature ds18b20(&oneWire);
WiFiClient        wifiClient;
PubSubClient      mqtt(wifiClient);

// ── Flota de 10 parcelas ──────────────────────────────────────────────────────

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

// ── Tiempo simulado ───────────────────────────────────────────────────────────
// 2025-05-01 00:00:00 UTC = 1746057600
unsigned long simEpoch    = 1746057600UL;
const unsigned long SIM_STEP = 10800UL;   // segundos simulados por publicación (3h)

unsigned long lastSample = 0;

// ── Funciones de red ──────────────────────────────────────────────────────────

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
  bool ok = (strlen(MQTT_USER) > 0)
      ? mqtt.connect(MQTT_CLIENT_ID, MQTT_USER, MQTT_PASS_STR)
      : mqtt.connect(MQTT_CLIENT_ID);
  if (ok) {
    Serial.println("[MQTT] Conectado");
  } else {
    Serial.printf("[MQTT] ERROR rc=%d\n", mqtt.state());
  }
}

// ── Utilidades ────────────────────────────────────────────────────────────────

String epochToISO8601(unsigned long epoch) {
  unsigned long e = epoch;
  int sec  = e % 60; e /= 60;
  int min  = e % 60; e /= 60;
  int hour = e % 24; e /= 24;

  unsigned long days = e;
  int year = 1970;
  while (true) {
    bool leap  = (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0));
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

// ── Preprocesamiento: media filtrada de un buffer ─────────────────────────────
// Descarta valores NaN y fuera del rango [minVal, maxVal].
// Devuelve NAN si no hay ningún valor válido.

float filteredMean(float* buf, int count, float minVal, float maxVal) {
  float sum   = 0.0f;
  int   valid = 0;
  for (int i = 0; i < count; i++) {
    if (isnan(buf[i])) continue;
    if (buf[i] < minVal || buf[i] > maxVal) continue;
    sum += buf[i];
    valid++;
  }
  return (valid > 0) ? (sum / (float)valid) : NAN;
}

// ── Muestreo: lectura y almacenamiento en buffers ─────────────────────────────

void sampleSensors() {
  ds18b20.requestTemperatures();

  float airTemp  = dht.readTemperature();
  float relHum   = dht.readHumidity();
  float soilTemp = ds18b20.getTempCByIndex(0);
  int   rawSoil  = analogRead(SOIL_PIN);

  // Temperatura aire (buffer 1)
  if (!isnan(airTemp) && bufAirTempCount < BUFFER_SIZE) {
    bufAirTemp[bufAirTempCount++] = airTemp;
  }

  // Temperatura suelo (buffer 2)
  if (soilTemp != DEVICE_DISCONNECTED_C && bufSoilTempCount < BUFFER_SIZE) {
    bufSoilTemp[bufSoilTempCount++] = soilTemp;
  }

  // Humedad ambiente + suelo (buffer 3, contador compartido)
  if (!isnan(relHum) && bufHumCount < BUFFER_SIZE) {
    float soilHum = (float)(SOIL_DRY_ADC - rawSoil) /
                    (float)(SOIL_DRY_ADC - SOIL_WET_ADC) * 100.0f;
    soilHum = constrain(soilHum, 0.0f, 100.0f);

    bufRelHum [bufHumCount] = relHum;
    bufSoilHum[bufHumCount] = soilHum;
    bufHumCount++;
  }

  Serial.printf("[Buffer] airTemp=%d/%d  soilTemp=%d/%d  hum=%d/%d\n",
                bufAirTempCount, BUFFER_SIZE,
                bufSoilTempCount, BUFFER_SIZE,
                bufHumCount, BUFFER_SIZE);
}

// ── Publicación: un ciclo completo con las medias preprocesadas ───────────────

void publishFleet(float avgAirTemp, float avgSoilTemp, float avgRelHum, float avgSoilHum) {
  String ts = epochToISO8601(simEpoch);

  for (int i = 0; i < FLEET_SIZE; i++) {
    Parcela& p = fleet[i];

    // Variación determinista por índice (±1.8 °C entre extremos de flota)
    float delta = (i - 4.5f) * 0.4f;

    float airTemp  = avgAirTemp  + delta;
    float soilTemp = avgSoilTemp + delta * 0.6f;
    float relHum   = avgRelHum   - delta * 0.8f;
    float soilHum  = constrain(avgSoilHum + i * 1.5f, 0.0f, 100.0f);

    // Aplicar fallbacks si la media no es válida
    if (isnan(airTemp))  airTemp  = 22.5f + delta;
    if (isnan(soilTemp)) soilTemp = 19.5f + delta * 0.6f;
    if (isnan(relHum))   relHum   = 62.0f - delta * 0.8f;
    if (isnan(soilHum))  soilHum  = constrain(45.0f + i * 1.5f, 0.0f, 100.0f);

    // Batería: descarga lenta
    p.battery_mv -= (float)random(0, 4) / 10.0f;
    if (p.battery_mv < 3300.0f) p.battery_mv = 3300.0f;

    char topic[80];
    snprintf(topic, sizeof(topic),
             "fincas/%s/parcelas/%s/lecturas", p.finca_id, p.parcela_id);

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
    delay(50);
  }

  simEpoch += SIM_STEP;
  Serial.printf("--- Ciclo publicado. Próximo ts: %s ---\n\n",
                epochToISO8601(simEpoch).c_str());
}

// ── Preprocesar buffers y publicar cuando estén llenos ───────────────────────

void processAndPublishIfReady() {
  // El ciclo se dispara cuando los 3 buffers han alcanzado BUFFER_SIZE
  if (bufAirTempCount  < BUFFER_SIZE) return;
  if (bufSoilTempCount < BUFFER_SIZE) return;
  if (bufHumCount      < BUFFER_SIZE) return;

  Serial.println("[Proceso] Buffers llenos — preprocesando...");

  float avgAirTemp  = filteredMean(bufAirTemp,  bufAirTempCount,  AIR_TEMP_MIN,  AIR_TEMP_MAX);
  float avgSoilTemp = filteredMean(bufSoilTemp, bufSoilTempCount, SOIL_TEMP_MIN, SOIL_TEMP_MAX);
  float avgRelHum   = filteredMean(bufRelHum,   bufHumCount,      REL_HUM_MIN,   REL_HUM_MAX);
  float avgSoilHum  = filteredMean(bufSoilHum,  bufHumCount,      SOIL_HUM_MIN,  SOIL_HUM_MAX);

  Serial.printf("[Medias] airTemp=%.2f  soilTemp=%.2f  relHum=%.2f  soilHum=%.2f\n",
                avgAirTemp, avgSoilTemp, avgRelHum, avgSoilHum);

  publishFleet(avgAirTemp, avgSoilTemp, avgRelHum, avgSoilHum);

  // Reiniciar buffers
  bufAirTempCount  = 0;
  bufSoilTempCount = 0;
  bufHumCount      = 0;
}

// ── Setup / Loop ──────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("=== AgroCollective Fleet Node v0.2 ===");
  Serial.printf("Flota: %d parcelas | Buffer: %d muestras | Intervalo: %lu s\n\n",
                FLEET_SIZE, BUFFER_SIZE, SAMPLE_INTERVAL / 1000UL);

  dht.begin();
  ds18b20.begin();

  connectWiFi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  connectMQTT();

  // Primera muestra inmediata para no esperar el primer intervalo
  lastSample = millis();
  sampleSensors();
}

void loop() {
  connectWiFi();
  connectMQTT();
  mqtt.loop();

  if (millis() - lastSample >= SAMPLE_INTERVAL) {
    lastSample = millis();
    sampleSensors();
    processAndPublishIfReady();
  }
}
