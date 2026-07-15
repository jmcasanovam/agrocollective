# Requisitos del sistema

## Requisitos funcionales

### RF-01 · Gestión de usuarios
- El sistema debe permitir el registro e inicio de sesión mediante email y contraseña.
- Las operaciones autenticadas deben rechazar usuarios con `is_active = false`.
- El token de acceso es JWT con expiración configurable.

### RF-02 · Gestión de fincas y parcelas
- Un usuario puede gestionar múltiples fincas.
- Cada finca pertenece a una región geográfica del catálogo.
- Cada finca puede tener múltiples parcelas con cultivo, tipo de suelo y perfil de gestión.

### RF-03 · Dispositivos IoT
- Cada parcela puede tener como máximo un dispositivo (nodo ESP32) registrado, forzado por `uq_device_plot_id` (constraint de BD) y verificado en `device_service.create` (409 si ya existe uno).
- Un dispositivo tiene asociado un array de sensores de la plataforma.
- Todos los dispositivos comparten el mismo catálogo de sensores (compatibilidad de plataforma).

### RF-04 · Catálogo de sensores
- La plataforma mantiene un catálogo de tipos de sensor: `air_temperature`, `relative_humidity`, `soil_temperature`, `soil_humidity`.
- Los sensores se pueden asignar y desasignar de dispositivos individualmente.
- El catálogo puede ampliarse sin modificar el código del firmware.

### RF-05 · Ingesta de mediciones
- Las mediciones llegan por MQTT en el tópico `devices/{device_code}/readings` (identificado por código de dispositivo, no por finca/parcela).
- El worker `mqtt_consumer.py` procesa y almacena cada mensaje en InfluxDB.
- Las mediciones incluyen: temperatura aire, temperatura suelo, humedad relativa del aire, humedad del suelo y batería.

### RF-06 · Catálogo de referencia
- El sistema mantiene tablas de referencia para cultivos, tipos de suelo y regiones.
- Estas tablas son accesibles públicamente (lectura) y modificables por usuarios autenticados.

### RF-07 · Análisis y recomendaciones
- El sistema debe agrupar parcelas similares mediante clustering K-Means.
- Debe detectar anomalías en las mediciones mediante Local Outlier Factor (LOF).
- Debe generar recomendaciones de riego y gestión basadas en parcelas análogas.

### RF-08 · Datos climáticos externos
- El sistema descarga datos de la API SiAR (MAPA) para las regiones registradas.
- Los datos climáticos (ETo, precipitación, temperatura) se almacenan en InfluxDB.

---

## Requisitos no funcionales

### RNF-01 · Seguridad
- Todas las contraseñas se almacenan con hash bcrypt.
- Las rutas de escritura requieren autenticación JWT.
- Las consultas a base de datos verifican que el `user_id` corresponda a un usuario activo.

### RNF-02 · Escalabilidad
- La arquitectura de workers permite escalar el procesamiento MQTT de forma independiente al backend HTTP.
- InfluxDB gestiona eficientemente miles de puntos por segundo de múltiples dispositivos.

### RNF-03 · Simulación IoT
- El firmware del ESP32 implementa buffers de 15 muestras con preprocesamiento (filtrado + promediado) antes de publicar.
- La simulación en Wokwi debe reproducir condiciones reales de 10 parcelas a partir de un único nodo físico.

### RNF-04 · Observabilidad
- El sistema expone endpoints `/health` y `/health/db` para monitorización.
- Los workers incluyen logging estructurado.

---

## Dependencias externas

| Dependencia | Uso | Obligatoria |
|-------------|-----|-------------|
| PostgreSQL 16 | Datos relacionales | Sí |
| InfluxDB 2.7 | Series temporales | Sí |
| Mosquitto MQTT | Mensajería IoT | Sí |
| API SiAR (MAPA) | Datos climáticos | No (solo scripts) |
| Wokwi | Simulación ESP32 | No (solo desarrollo) |

---

## Entorno de desarrollo

- Python 3.11+
- Docker y Docker Compose v2
- Arduino CLI o extensión Wokwi para VSCode (simulación IoT)

Ver [wokwi-deployment.md](wokwi-deployment.md) para la guía de simulación del nodo IoT.
