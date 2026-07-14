/*
 * AgroCollective - Nodo IoT completo para una única parcela
 * ESP32 DevKit C V4
 *
 * Línea de trabajo futuro: dispositivo de campo con los 5 sensores
 * necesarios para una parcela completa (no la flota de simulación actual).
 *
 * Sensores físicos:
 *   GPIO 15      → DHT22   (temperatura aire + humedad relativa)
 *   GPIO  5      → DS18B20 (temperatura suelo, OneWire)
 *   GPIO 34      → Sensor capacitivo humedad suelo (ADC1_CH6)
 *                  No existe como parte nativa en Wokwi: se ha creado un
 *                  chip personalizado (soil-moisture-sensor.chip.c/json)
 *                  que simula un DFRobot SEN0193.
 *   GPIO 21/22   → BMP280  (presión atmosférica, I2C)
 *
 * Identificadores del dispositivo:
 *   finca_id, parcela_id y esp32_id ya están generados y se hardcodean
 *   aquí abajo (no se generan en runtime; en producción los asignaría
 *   el backend al dar de alta el dispositivo).
 *
 * Publicación:
 *   Cada lectura se envía a un bróker MQTT en el tópico
 *   fincas/{finca_id}/parcelas/{parcela_id}/lecturas
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_BMP280.h>
#include <ArduinoJson.h>

// ── Variables de conexión ──────────────────────────────────────────────────
// Sustituir por credenciales reales; no tienen por qué existir en este entorno.

const char* WIFI_SSID      = "Wokwi-GUEST";
const char* WIFI_PASS      = "";
const char* MQTT_BROKER    = "broker.hivemq.com";
const int   MQTT_PORT      = 1883;
const char* MQTT_CLIENT_ID = "agrocollective-nodo-P001";
const char* MQTT_USER      = "";   // dejar vacío si no hay autenticación
const char* MQTT_PASS_STR  = "";   // dejar vacío si no hay autenticación

// ── Identificadores del dispositivo (ya generados, hardcodeados) ──────────

const char* FINCA_ID   = "F001";
const char* PARCELA_ID = "P001";
const char* ESP32_ID   = "ESP-P001";

// ── Pines ───────────────────────────────────────────────────────────────────

#define DHT_PIN  15
#define DHT_TYPE DHT22
#define DS_PIN    5
#define SOIL_PIN 34

// SEN0193: seco ~2800 (ADC 12-bit), mojado ~1200
#define SOIL_DRY_ADC  2800
#define SOIL_WET_ADC  1200

#define SAMPLE_INTERVAL 60000UL   // ms entre lecturas y publicaciones (1 minuto)

// ── Objetos hardware ────────────────────────────────────────────────────────

DHT               dht(DHT_PIN, DHT_TYPE);
OneWire           oneWire(DS_PIN);
DallasTemperature ds18b20(&oneWire);
Adafruit_BMP280   bmp;
WiFiClient        wifiClient;
PubSubClient      mqtt(wifiClient);

unsigned long lastSample = 0;

// ── Funciones de red ─────────────────────────────────────────────────────────

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
    Serial.printf("[WiFi] OK - IP: %s\n", WiFi.localIP().toString().c_str());
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

// ── Lectura y publicación de la parcela ──────────────────────────────────────

void readAndPublish() {
  ds18b20.requestTemperatures();

  float airTemp  = dht.readTemperature();
  float relHum   = dht.readHumidity();
  float soilTemp = ds18b20.getTempCByIndex(0);
  int   rawSoil  = analogRead(SOIL_PIN);
  float pressure = bmp.readPressure() / 100.0f;   // Pa → hPa

  float soilHum = (float)(SOIL_DRY_ADC - rawSoil) /
                  (float)(SOIL_DRY_ADC - SOIL_WET_ADC) * 100.0f;
  soilHum = constrain(soilHum, 0.0f, 100.0f);

  if (isnan(airTemp) || isnan(relHum) || soilTemp == DEVICE_DISCONNECTED_C) {
    Serial.println("[Lectura] ERROR: sensor desconectado o lectura inválida, se omite ciclo");
    return;
  }

  char topic[80];
  snprintf(topic, sizeof(topic),
           "fincas/%s/parcelas/%s/lecturas", FINCA_ID, PARCELA_ID);

  StaticJsonDocument<256> doc;
  doc["finca_id"]            = FINCA_ID;
  doc["parcela_id"]          = PARCELA_ID;
  doc["esp32_id"]            = ESP32_ID;
  doc["air_temp"]            = round(airTemp    * 10.0f) / 10.0f;
  doc["relative_humidity"]   = round(relHum     * 10.0f) / 10.0f;
  doc["soil_temp"]           = round(soilTemp   * 10.0f) / 10.0f;
  doc["soil_humidity"]       = round(soilHum    * 10.0f) / 10.0f;
  doc["atmospheric_pressure"] = round(pressure  * 10.0f) / 10.0f;

  char payload[256];
  serializeJson(doc, payload);

  bool ok = mqtt.publish(topic, payload);
  Serial.printf("[%s/%s] (%s) %s\n", FINCA_ID, PARCELA_ID, ok ? "OK" : "FAIL", payload);
}

// ── Setup / Loop ──────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("=== AgroCollective - Nodo IoT parcela unica ===");
  Serial.printf("Dispositivo: %s | Finca: %s | Parcela: %s\n", ESP32_ID, FINCA_ID, PARCELA_ID);

  dht.begin();
  ds18b20.begin();
  if (!bmp.begin(0x76)) {
    Serial.println("[BMP280] ERROR: sensor no encontrado");
  }

  connectWiFi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  connectMQTT();

  // Primera lectura inmediata para no esperar el primer intervalo
  lastSample = millis();
  readAndPublish();
}

void loop() {
  connectWiFi();
  connectMQTT();
  mqtt.loop();

  if (millis() - lastSample >= SAMPLE_INTERVAL) {
    lastSample = millis();
    readAndPublish();
  }
}
