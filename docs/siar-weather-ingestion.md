# Ingesta de datos meteorológicos SiAR

## Descripción

Las parcelas monitorizadas por AgroCollective generan lecturas propias de temperatura y humedad, pero carecen de contexto climático regional: precipitación, evapotranspiración, radiación. Ese contexto lo aporta el Sistema de Información Agroclimática para el Regadío (SiAR), del Ministerio de Agricultura, Pesca y Alimentación, a través de dos estaciones de referencia —V17 (Valencia) y GR01 (Baza)— que sirven de proxy meteorológico para las regiones cubiertas por el proyecto.

El script `scripts/download_siar.py` descarga el histórico diario de ambas estaciones, lo valida, interpola los huecos breves y lo escribe en InfluxDB, junto con una agregación semanal calculada localmente para el histórico y una tarea Flux que mantiene esa agregación al día en adelante. Es idempotente: ejecutarlo varias veces no duplica puntos, porque InfluxDB sobrescribe cualquier registro que comparta timestamp y etiquetas.

---

## Variables de entorno

El script y el contenedor de InfluxDB leen las siguientes claves del `.env` de la raíz del proyecto:

```dotenv
# InfluxDB
INFLUXDB_HOST=localhost
INFLUXDB_PORT=8086
INFLUXDB_INIT_USERNAME=admin
INFLUXDB_INIT_PASSWORD=admin_password_123
INFLUXDB_TOKEN=my-super-secret-influxdb-token-for-dev-123
INFLUXDB_ORG=agrocollective
INFLUXDB_BUCKET_WEATHER=agrocollective_siar

# SiAR
SIAR_TOKEN=
```

Conviene distinguir dos momentos en la vida de estas variables. `INFLUXDB_INIT_USERNAME`, `INFLUXDB_INIT_PASSWORD` e `INFLUXDB_TOKEN` solo tienen efecto en el arranque inicial del contenedor de InfluxDB, es decir, cuando el volumen `influxdb_data` está vacío: en ese momento, `docker-compose.yml` los traslada a las variables nativas de la imagen oficial (`DOCKER_INFLUXDB_INIT_USERNAME`, `DOCKER_INFLUXDB_INIT_PASSWORD`, `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN`) y InfluxDB los adopta como credenciales del administrador. Una vez creado el volumen, modificar estos valores en el `.env` no cambia nada en el servidor ya inicializado; solo servirían si se destruye el volumen y se vuelve a arrancar desde cero.

`INFLUXDB_ORG` y `INFLUXDB_BUCKET_WEATHER` sí se usan en cada ejecución, para saber a qué organización y a qué bucket dirigir las escrituras.

---

## De dónde salen los tokens

### Token de InfluxDB

No hace falta generarlo manualmente si el volumen de InfluxDB aún no existe: basta con escribir cualquier cadena razonablemente larga en `INFLUXDB_TOKEN` antes del primer `docker compose up`, y esa cadena se convierte en el token de administrador con acceso total. Es el camino que se ha seguido en este proyecto.

Si en cambio InfluxDB ya está inicializado y se necesita un token nuevo —por ejemplo, uno con permisos más restringidos, o porque el original se ha perdido—, se genera desde la interfaz web:

1. Entrar en `http://localhost:8086` con el usuario y contraseña de administrador.
2. Ir a **Load Data → API Tokens → Generate API Token → All Access API Token**.
3. Copiar el token generado a `INFLUXDB_TOKEN` en el `.env` y reiniciar el contenedor `backend` para que lo recoja.

### Token de SiAR

El acceso a la Web API de SiAR requiere darse de alta como usuario en el sistema y, específicamente, solicitar el alta en la API: desde la web de SiAR, en **Mi SiAR → Editar perfil**, activando la opción «Deseo darme de alta en API SiAR». El token permanente asociado a esa cuenta se obtiene igualmente desde la web del MAPA (`https://servicio.mapa.gob.es/siarapi`) y es el que corresponde a `SIAR_TOKEN` en el `.env`.

Como vía alternativa, el manual de la API SiAR (v2.2) describe un procedimiento programático para obtener tokens de sesión, pensado para integraciones que no dependan de un token permanente ya emitido:

1. Cifrar el NIF del usuario: `GET {BaseURL}/API/V1/Autenticacion/cifrarCadena?cadena={NIF}`
2. Cifrar la contraseña con el mismo método: `GET {BaseURL}/API/V1/Autenticacion/cifrarCadena?cadena={password}`
3. Canjear ambas cadenas cifradas por un token: `GET {BaseURL}/API/V1/Autenticacion/obtenerToken?Usuario={NIF_cifrado}&Password={password_cifrada}`

Un matiz importante, descubierto al poner el script en marcha con datos reales: un token válido no da acceso ilimitado al histórico. SiAR autoriza cada token a partir de una fecha mínima —en el caso del token actualmente configurado, el 23 de junio de 2025—, y cualquier consulta anterior a esa fecha se rechaza con un HTTP 403 cuyo mensaje menciona explícitamente una «Fecha Mínima Inicial autorizada». No es un fallo de autenticación, sino una restricción de alcance del propio token, y el script la distingue como tal en sus mensajes de error en lugar de confundirla con un token inválido.

---

## Ejecutar la descarga

Con los contenedores levantados (`docker compose up -d`), la descarga se lanza dentro del contenedor `backend`:

```bash
docker compose exec backend python scripts/download_siar.py
```

Antes de tocar la red, el script valida el token contra el servicio `Info/ACCESOS` de SiAR y comprueba que InfluxDB responde; si alguna de las dos cosas falla, lo dice de forma explícita —token inválido o caducado, InfluxDB inalcanzable— en vez de dejar que el error aparezca más adelante, a mitad de una descarga larga, con un mensaje genérico.

Superada esa comprobación, el script consulta cuál es la última fecha con datos ya almacenada en el bucket de clima. Si no encuentra ninguna, descarga el histórico completo desde la constante `DATE_START` (fijada en el propio script, actualmente el 23 de junio de 2025, por la restricción de token descrita arriba); si ya hay datos, retoma la descarga justo donde se quedó. La petición se trocea en bloques de 28 días —el límite razonable frente al rate-limit de SiAR— y, si la API responde con un 429 o un 403 de límite de peticiones, el script espera y reintenta con una espera creciente (30, 60 y 120 segundos) antes de darse por vencido.

Como SiAR no siempre tiene publicado el dato del propio día en curso, el script no exige que el rango llegue hasta hoy a toda costa: recorta la fecha final, estación por estación, a la última fecha con datos realmente recibidos, y solo entonces valida huecos e interpola los que sean de una semana o menos.

Al terminar, escribe los puntos diarios en la serie `weather` y los semanales agregados en `weather_weekly`, ambas dentro del bucket definido por `INFLUXDB_BUCKET_WEATHER`, y crea (o actualiza, si ya existe) una tarea Flux llamada `weather_weekly_downsampling` que recalcula la agregación semanal cada día a partir de ese momento, sin necesidad de volver a ejecutar el script manualmente para mantenerla al día.

Para comprobar el comportamiento sin escribir nada, existe el modo de prueba:

```bash
docker compose exec backend python scripts/download_siar.py --dry-run
```

Este modo recorre toda la descarga, la validación y la interpolación, pero se detiene justo antes de escribir en InfluxDB; es la manera más segura de verificar que un token nuevo funciona o de revisar el estado de los datos sin riesgo de alterar lo ya almacenado.

---

## Comprobar el resultado

En `http://localhost:8086`, con las credenciales de administrador, el camino más directo es **Data Explorer**: seleccionar el bucket `agrocollective_siar`, el measurement `weather` (o `weather_weekly`) y, si se desea, filtrar por `siar_station_code` o `region_code`. El único detalle que suele despistar es el selector de rango temporal, que por defecto muestra solo la última hora; como los datos son diarios y se remontan a mediados de 2025, hay que ampliarlo a un rango que los cubra, o sustituirlo por una consulta Flux explícita:

```flux
from(bucket: "agrocollective_siar")
  |> range(start: 2025-06-23)
  |> filter(fn: (r) => r._measurement == "weather")
```
