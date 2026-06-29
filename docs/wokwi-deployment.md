# Despliegue en Wokwi

Guía paso a paso para simular el nodo IoT de AgroCollective usando [Wokwi](https://wokwi.com), un simulador de hardware embebido que corre en el navegador sin necesidad de placa física.

---

## Índice

1. [¿Qué simula el nodo?](#1-qué-simula-el-nodo)
2. [Archivos relevantes](#2-archivos-relevantes)
3. [Requisitos previos](#3-requisitos-previos)
4. [Circuito: componentes y conexiones](#4-circuito-componentes-y-conexiones)
5. [Firmware: arquitectura y variables](#5-firmware-arquitectura-y-variables)
6. [Lógica de buffer y preprocesamiento](#6-lógica-de-buffer-y-preprocesamiento)
7. [Cómo lanzar la simulación](#7-cómo-lanzar-la-simulación)
8. [Flujo de datos hasta el backend](#8-flujo-de-datos-hasta-el-backend)
9. [Ajuste del broker MQTT](#9-ajuste-del-broker-mqtt)
10. [Salida esperada](#10-salida-esperada)
11. [Limitaciones de la simulación](#11-limitaciones-de-la-simulación)

---

## 1. ¿Qué simula el nodo?

El nodo simula una **flota de 10 parcelas agrícolas** conectadas a un único ESP32. Cada ciclo de publicación genera variaciones deterministas por parcela a partir de una única lectura base de los sensores físicos, reproduciendo condiciones distintas de temperatura y humedad entre parcelas de distintas regiones (VALENCIA y BAZA).

Los sensores físicos reales que modela el circuito son:

| Sensor | Tipo | Magnitudes |
|--------|------|-----------|
| DHT22 | Digital, 1-Wire | Temperatura ambiente (°C), Humedad relativa (%) |
| DS18B20 | Digital, OneWire | Temperatura del suelo (°C) |
| SEN0193 | Analógico, ADC | Humedad del suelo (%) |

---

## 2. Archivos relevantes

```
wokwi/
├── sketch.ino                   ← Firmware del ESP32
├── diagram.json                 ← Circuito (componentes + conexiones)
├── libraries.txt                ← Librerías Arduino necesarias
├── soil-moisture-sensor.chip.c  ← Chip personalizado: sensor capacitivo
└── soil-moisture-sensor.chip.json
```

Wokwi carga automáticamente todos los archivos de la carpeta cuando se abre el proyecto.

---

## 3. Requisitos previos

### Opción A — Wokwi web (recomendado para pruebas rápidas)

1. Crear cuenta gratuita en [wokwi.com](https://wokwi.com).
2. Crear un nuevo proyecto de tipo **ESP32**.
3. Reemplazar los ficheros del proyecto con los de la carpeta `wokwi/`.

### Opción B — Extensión VSCode

1. Instalar la extensión [Wokwi for VS Code](https://marketplace.visualstudio.com/items?itemName=wokwi.wokwi-vscode).
2. Abrir la carpeta `wokwi/` en VS Code.
3. Pulsar `F1` → **Wokwi: Start Simulator**.

> La extensión de VSCode requiere una licencia de Wokwi (plan gratuito o de pago). Ver [wokwi.com/pricing](https://wokwi.com/pricing).

---

## 4. Circuito: componentes y conexiones

### Componentes

| ID | Tipo | Descripción |
|----|------|-------------|
| `esp` | `wokwi-esp32-devkit-v1` | Microcontrolador principal |
| `dht1` | `wokwi-dht22` | Sensor temp. ambiente + humedad relativa |
| `ds1` | `wokwi-ds18b20` | Sensor temperatura del suelo |
| `r1` | `wokwi-resistor` (4 700 Ω) | Pull-up para bus OneWire del DS18B20 |
| `soil1` | `soil-moisture-sensor` (chip custom) | Sensor capacitivo humedad suelo |

### Conexiones

```
ESP32       DHT22
3V3    →   VCC
GND    →   GND
GPIO15 →   SDA

ESP32       DS18B20       Resistor 4k7
3V3    →   VDD
3V3    →   R1 pin 1
R1 pin 2 → DQ
GPIO5  →   DQ
GND    →   GND

ESP32       SEN0193 (chip custom)
3V3    →   VCC
GND    →   GND
GPIO34 →   AOUT
```

La resistencia pull-up de 4 700 Ω es obligatoria para el protocolo OneWire del DS18B20; sin ella el sensor no responde.

GPIO34 es un pin exclusivamente de entrada (ADC1_CH6) del ESP32, adecuado para leer la señal analógica del sensor capacitivo.

### Ajuste de valores iniciales en el simulador

En `diagram.json` los atributos `temperature`, `humidity` y `moisture` definen los valores de partida de cada sensor en Wokwi:

```json
{ "type": "wokwi-dht22",  "attrs": { "temperature": "22.5", "humidity": "62" } }
{ "type": "wokwi-ds18b20","attrs": { "temperature": "19.5" } }
{ "type": "soil-moisture-sensor", "attrs": { "moisture": "45" } }
```

Puedes modificarlos directamente o usar los sliders del simulador en tiempo de ejecución.

---

## 5. Firmware: arquitectura y variables

### Variables de conexión

Al inicio de `sketch.ino` se declaran todas las credenciales necesarias. En Wokwi se usan valores de ejemplo; en producción se sustituyen por los reales:

```cpp
const char* WIFI_SSID      = "Wokwi-GUEST"; // red virtual de Wokwi (sin contraseña)
const char* WIFI_PASS      = "";
const char* MQTT_BROKER    = "broker.hivemq.com"; // broker público para pruebas
const int   MQTT_PORT      = 1883;
const char* MQTT_CLIENT_ID = "agrocollective-fleet-001";
const char* MQTT_USER      = "";  // vacío → sin autenticación
const char* MQTT_PASS_STR  = "";
```

> `Wokwi-GUEST` es la red WiFi virtual integrada en Wokwi que permite conexión a internet desde la simulación.

### Parámetros de buffer

```cpp
#define BUFFER_SIZE     15       // muestras por ventana (≈ 15 minutos reales)
#define SAMPLE_INTERVAL 60000UL  // milisegundos entre muestras (1 min)
```

### Rangos de filtrado

Definen qué valores se consideran válidos antes de calcular la media:

```cpp
#define AIR_TEMP_MIN   -10.0f   // °C
#define AIR_TEMP_MAX    60.0f
#define SOIL_TEMP_MIN   -5.0f
#define SOIL_TEMP_MAX   50.0f
#define REL_HUM_MIN      0.0f   // %
#define REL_HUM_MAX    100.0f
#define SOIL_HUM_MIN     0.0f
#define SOIL_HUM_MAX   100.0f
```

### Tiempo simulado

Cada publicación avanza 3 horas de tiempo simulado, partiendo del 2025-05-01 00:00:00 UTC:

```cpp
unsigned long simEpoch = 1746057600UL; // epoch Unix de 2025-05-01T00:00:00Z
const unsigned long SIM_STEP = 10800UL; // 3 h en segundos
```

Esto permite generar una serie temporal histórica realista sin esperar semanas de ejecución.

---

## 6. Lógica de buffer y preprocesamiento

El firmware implementa un pipeline de tres etapas antes de enviar datos al broker:

```
[Sensores físicos]
       │  (cada 60 s)
       ▼
[sampleSensors()]
  ├─ bufAirTemp[15]    ← temperatura ambiente
  ├─ bufSoilTemp[15]   ← temperatura del suelo
  └─ bufRelHum[15]     ← humedad relativa
     bufSoilHum[15]    ← humedad del suelo (contador compartido)
       │  (cuando los 3 buffers llegan a 15 muestras)
       ▼
[filteredMean()]       ← Preprocesamiento por buffer
  1. Descarta valores NaN (sensor desconectado)
  2. Descarta valores fuera del rango normal
  3. Calcula la media aritmética de los valores válidos
       │
       ▼
[publishFleet()]
  Para cada una de las 10 parcelas:
  ├─ Aplica variación determinista por índice (±1.8 °C)
  ├─ Publica mensaje JSON por MQTT
  └─ Avanza el timestamp simulado (+3 h)
       │
       ▼
  Reinicio de los 3 buffers (buffers a 0)
```

### Ejemplo de ciclo completo

```
[Buffer] airTemp= 1/15  soilTemp= 1/15  hum= 1/15
[Buffer] airTemp= 2/15  soilTemp= 2/15  hum= 2/15
...
[Buffer] airTemp=15/15  soilTemp=15/15  hum=15/15
[Proceso] Buffers llenos — preprocesando...
[Medias] airTemp=23.10  soilTemp=19.80  relHum=61.40  soilHum=46.30
[F001/P001] (OK) {"finca_id":"F001","parcela_id":"P001",...}
...
[F005/P002] (OK) {"finca_id":"F005","parcela_id":"P010",...}
--- Ciclo publicado. Próximo ts: 2025-05-01T06:00:00Z ---
```

---

## 7. Cómo lanzar la simulación

### En Wokwi web

1. Ir a [wokwi.com](https://wokwi.com) e iniciar sesión.
2. Crear proyecto → **New Project** → **ESP32**.
3. En el panel de archivos, reemplazar o pegar el contenido de:
   - `sketch.ino`
   - `diagram.json`
   - `libraries.txt`
4. Añadir los archivos del chip custom:
   - `soil-moisture-sensor.chip.c`
   - `soil-moisture-sensor.chip.json`
5. Pulsar **▶ Play** (o `F9`).
6. Wokwi compilará automáticamente el sketch y arrancará la simulación.

### En VSCode (extensión Wokwi)

1. Abrir la carpeta `wokwi/` en VS Code.
2. Asegurarse de que hay un fichero `wokwi.toml` en la raíz (si no existe, la extensión lo crea la primera vez).
3. Pulsar `F1` → **Wokwi: Start Simulator**.
4. El simulador se abrirá en un panel lateral.

> **Nota**: para compilar el sketch fuera de Wokwi web se necesita el toolchain ESP32 para Arduino (o PlatformIO). La extensión de VSCode puede compilar directamente si está configurada con `arduino-cli` o PlatformIO.

---

## 8. Flujo de datos hasta el backend

```
[Wokwi — ESP32]
    │  MQTT publish
    │  Tópico: fincas/{finca_id}/parcelas/{parcela_id}/lecturas
    │  Payload: JSON (ver abajo)
    ▼
[Broker MQTT]
  broker.hivemq.com:1883  ← simulación (broker público)
  mosquitto:1883           ← producción (Docker Compose)
    │
    │  MQTT subscribe
    ▼
[mqtt_consumer.py]  ← worker Python del backend
    │
    ├─ Escribe en InfluxDB (series temporales)
    └─ Actualiza estado en PostgreSQL
```

### Formato del mensaje publicado

```json
{
  "finca_id":          "F001",
  "parcela_id":        "P001",
  "esp32_id":          "ESP-P001",
  "timestamp":         "2025-05-01T03:00:00Z",
  "soil_humidity":     46.3,
  "soil_temp":         19.8,
  "air_temp":          23.1,
  "relative_humidity": 61.4,
  "battery_mv":        4198,
  "depth_cm":          30
}
```

Los campos `soil_humidity`, `soil_temp`, `air_temp` y `relative_humidity` son las **medias preprocesadas** de los 15 minutos de ventana, con la variación por parcela aplicada encima.

---

## 9. Ajuste del broker MQTT

### Simulación (por defecto)

El sketch usa `broker.hivemq.com` (broker público MQTT sin autenticación). No requiere configuración adicional.

Para suscribirse manualmente al tópico desde la terminal y ver los mensajes en tiempo real:

```bash
# con mosquitto_sub instalado localmente
mosquitto_sub -h broker.hivemq.com -p 1883 -t "fincas/#"

# o con MQTT Explorer (GUI): conectar a broker.hivemq.com:1883
```

### Integración con el backend local (Docker)

Para que el ESP32 simulado envíe datos al backend de Docker Compose, cambiar el broker en `sketch.ino`:

```cpp
// Sustituir por la IP de la máquina host (no "localhost" — Wokwi es remoto)
const char* MQTT_BROKER = "YOUR_HOST_IP";
const int   MQTT_PORT   = 1883;
```

Y asegurarse de que el servicio Mosquitto en `docker-compose.yml` tiene el puerto 1883 expuesto y acepta conexiones externas. Revisar `docker/mosquitto/mosquitto.conf`:

```conf
listener 1883
allow_anonymous true
```

> En Wokwi web la simulación corre en la nube de Wokwi, por lo que el broker debe ser accesible desde internet (IP pública o servicio como HiveMQ Cloud). En la extensión VSCode la simulación corre localmente y puede conectar a `localhost`.

---

## 10. Salida esperada

En el **Serial Monitor** de Wokwi se verá:

```
=== AgroCollective Fleet Node v0.2 ===
Flota: 10 parcelas | Buffer: 15 muestras | Intervalo: 60 s

[WiFi] Conectando a 'Wokwi-GUEST'...
..
[WiFi] OK — IP: 10.10.0.5
[MQTT] Conectando a broker.hivemq.com:1883...
[MQTT] Conectado
[Buffer] airTemp= 1/15  soilTemp= 1/15  hum= 1/15
[Buffer] airTemp= 2/15  soilTemp= 2/15  hum= 2/15
...
[Buffer] airTemp=15/15  soilTemp=15/15  hum=15/15
[Proceso] Buffers llenos — preprocesando...
[Medias] airTemp=23.10  soilTemp=19.80  relHum=61.40  soilHum=46.30
[F001/P001] (OK) {"finca_id":"F001","parcela_id":"P001","esp32_id":"ESP-P001","timestamp":"2025-05-01T03:00:00Z","soil_humidity":46.6,"soil_temp":19.6,"air_temp":21.3,"relative_humidity":62.8,"battery_mv":4198,"depth_cm":30}
...
[F005/P002] (OK) {"finca_id":"F005","parcela_id":"P010",...}
--- Ciclo publicado. Próximo ts: 2025-05-01T06:00:00Z ---
```

Cada ciclo completo de publicación tarda **15 minutos reales** (15 muestras × 60 s). Para acelerar la simulación en desarrollo, reducir `SAMPLE_INTERVAL` y/o `BUFFER_SIZE` en `sketch.ino`.

---

## 11. Limitaciones de la simulación

| Limitación | Descripción |
|-----------|-------------|
| **Un solo nodo físico** | El ESP32 simula 10 parcelas mediante variaciones matemáticas, no 10 hardware independientes. |
| **Valores de sensor estáticos por defecto** | Los atributos `temperature`/`humidity`/`moisture` del `diagram.json` son fijos; para variarlos en tiempo real se usan los sliders del simulador. |
| **Sin persistencia de batería** | La descarga de batería simulada se reinicia cada vez que se arranca la simulación. |
| **Tiempo simulado no real** | `SIM_STEP = 10 800 s` (3 h) por publicación; la serie temporal generada avanza mucho más rápido que el tiempo real. |
| **MQTT sin TLS** | El broker público HiveMQ se usa sin autenticación ni cifrado. En producción usar un broker propio con TLS. |
| **Sin `device_code` real** | Los `esp32_id` del firmware (`ESP-P001` … `ESP-P010`) son provisionales y deben sustituirse por los `code` reales registrados en la API tras el seed de datos. |
