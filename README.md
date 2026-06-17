# EVA — Asistente Virtual de Recepción
### Proyecto SAGE · AHK 2026

EVA es el módulo conversacional del sistema SAGE. Recibe invitados, responde consultas del evento, orienta dentro del venue y recopila feedback, usando modelos locales sin depender de APIs externas en runtime.

> **Forma intended de correr este proyecto:** Docker Compose.  
> La ejecución local con Python/Ollama/Piper instalados a mano queda como modo legacy para debug puntual.

---

## Stack

| Componente | Tecnología | Nota |
|---|---|---|
| API | FastAPI + Uvicorn | Servicio `sage-agent` |
| LLM | Ollama | Servicio `ollama` |
| Modelo de lenguaje | `llama3.2:3b` | Configurable por `.env` |
| Embeddings | `nomic-embed-text` | Se usa vía `/api/embed` |
| TTS | Piper TTS | Binario incluido en la imagen del backend |
| Voz TTS | `es_AR-daniela-high` | Descargada automáticamente por `piper-init` |
| Deploy recomendado | Docker Compose | Local, rack y Dokploy |
| Persistencia | Volúmenes Docker | `ollama_models`, `piper_models`, `sage_data` |

---

## Arquitectura Docker Compose

El proyecto se levanta con estos servicios:

| Servicio | Responsabilidad |
|---|---|
| `ollama` | Expone Ollama dentro de la red Docker y carga los modelos LLM/embeddings. |
| `ollama-init` | Descarga automáticamente `OLLAMA_MODEL` y `OLLAMA_EMBED_MODEL` si no están presentes. Termina con exit `0`. |
| `piper-init` | Descarga automáticamente `es_AR-daniela-high.onnx` y `es_AR-daniela-high.onnx.json` en el volumen de Piper. Termina con exit `0`. |
| `sage-agent` | API FastAPI de EVA. Espera a que `ollama-init` y `piper-init` terminen correctamente antes de arrancar. |

Volúmenes usados:

| Volumen | Montaje | Uso |
|---|---|---|
| `ollama_models` | `/root/.ollama` | Modelos de Ollama. |
| `piper_models` | `/app/piper/models` | Modelo y config de voz de Piper. |
| `sage_data` | `/app/data` | Datos persistentes de la app. No montar `/app/app`. |

> Importante: nunca montar un volumen sobre `/app/app`, porque eso pisa el código copiado dentro de la imagen y puede dejar corriendo código viejo.

---

## Requisitos previos

### Local / WSL2

- Windows 10/11 con WSL2 y Ubuntu, o Linux nativo.
- Docker Engine.
- Docker Compose plugin (`docker compose`, no necesariamente `docker-compose`).
- Internet en el primer arranque para descargar modelos de Ollama y Piper.

### Instalar Docker y Docker Compose en Ubuntu

Si Docker no está instalado:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Permitir usar Docker sin `sudo`:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Verificar:

```bash
docker --version
docker compose version
```

---

## Configuración inicial

### 1. Clonar el repositorio

```bash
git clone https://github.com/SAGE-AHK/sage-agent.git
cd sage-agent
```

### 2. Crear `.env`

```bash
cp .env.example .env
```

Para Docker Compose, usar valores de este estilo:

```env
API_HOST=0.0.0.0
API_PORT=8000

START_OLLAMA=false

OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_NUM_PARALLEL=4
OLLAMA_REQUEST_TIMEOUT=30

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

PIPER_BIN=/app/piper/piper/piper
PIPER_MODEL=/app/piper/models/es_AR-daniela-high.onnx

SAGE_DATA_DIR=/app/data
PROMPT_SOURCE=hardcoded
```

Notas:

- `OLLAMA_BASE_URL` debe ser `http://ollama:11434` dentro de Docker.
- `START_OLLAMA=false` porque Ollama corre como servicio separado.
- `PIPER_BIN` y `PIPER_MODEL` deben apuntar a rutas internas del container.
- Para usar el front desde otra máquina/tótem, agregar su origen a `CORS_ORIGINS`.

---

## Correr con Docker Compose

### Levantar todo

```bash
docker compose up -d --build
```

Esto hace:

1. build de `sage-agent`;
2. arranque de `ollama`;
3. descarga automática de modelos con `ollama-init`;
4. descarga automática de voz Piper con `piper-init`;
5. arranque de la API cuando todo lo anterior terminó bien.

### Ver logs limpios del backend

```bash
docker compose logs -f --tail=100 sage-agent
```

### Ver estado de servicios

```bash
docker compose ps
```

Un estado normal es:

```text
ollama       running / healthy
ollama-init  exited (0)
piper-init   exited (0)
sage-agent   running
```

`ollama-init` y `piper-init` deben terminar; no quedan corriendo.

---

## Comandos útiles de Docker Compose

### Detener servicios sin borrar volúmenes

```bash
docker compose down
```

### Levantar de nuevo sin rebuild

```bash
docker compose up -d
```

### Rebuild limpio del backend

```bash
docker compose build --no-cache sage-agent
docker compose up -d
```

### Ver logs por servicio

```bash
docker compose logs -f sage-agent
docker compose logs -f ollama
docker compose logs -f ollama-init
docker compose logs -f piper-init
```

### Reset completo: borrar containers, red y volúmenes

```bash
docker compose down -v
docker compose up -d --build
```

Esto borra:

- modelos de Ollama (`ollama_models`);
- modelo de Piper (`piper_models`);
- datos persistentes de la app (`sage_data`).

En el siguiente arranque se descargan los modelos nuevamente.

### Borrar solo un volumen específico

Listar volúmenes:

```bash
docker volume ls | grep sage
```

Borrar solo Piper, por ejemplo:

```bash
docker compose down
docker volume rm sage-agent_piper_models
docker compose up -d
```

Borrar solo Ollama:

```bash
docker compose down
docker volume rm sage-agent_ollama_models
docker compose up -d
```

El nombre exacto puede variar según el nombre de carpeta/proyecto de Compose.

### Ejecutar comandos dentro del backend

```bash
docker compose exec sage-agent sh
```

Verificar Piper:

```bash
docker compose exec sage-agent sh -lc '
echo "PIPER_BIN=$PIPER_BIN"
echo "PIPER_MODEL=$PIPER_MODEL"
ls -lah "$PIPER_BIN"
ls -lah "$PIPER_MODEL"
ls -lah "$PIPER_MODEL.json"
'
```

Verificar código dentro de la imagen:

```bash
docker compose run --rm --no-deps --entrypoint sh sage-agent -lc \
  "nl -ba /app/app/embeddings.py | sed -n '1,130p'"
```

---

## Validación end-to-end

### Backend online

```bash
curl -s http://localhost:8000/ | python3 -m json.tool
```

Esperado:

```json
{ "status": "EVA online" }
```

### Chat

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"mensaje":"Hola EVA, ¿dónde es la acreditación?"}' | python3 -m json.tool
```

El body correcto usa `mensaje`, no `message`.

### Streaming SSE

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"mensaje":"¿Dónde están los baños?"}'
```

### TTS

```bash
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"texto":"Hola, soy EVA. Bienvenido al evento."}' \
  --output /tmp/eva_tts.wav

file /tmp/eva_tts.wav
ls -lh /tmp/eva_tts.wav
```

Esperado:

```text
/tmp/eva_tts.wav: RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, mono 22050 Hz
```

Si el archivo aparece como `JSON text data`, Piper falló y el backend devolvió JSON en vez de audio. Revisar `piper-init`, existencia del modelo y logs de `sage-agent`.

---

## Multisesión y roles

EVA soporta múltiples sesiones conversacionales usando un único backend y un único modelo de lenguaje. Esto permite correr varios tótems en simultáneo sin mezclar historiales de conversación.

Cada sesión se identifica por la combinación:

```text
rol:totem_id
```

Ejemplos:

```text
asistente:default
recepcionista:totem-A
asistente:totem-2
```

### Campos de sesión

| Campo      | Obligatorio | Default     | Descripción                                                                  |
| ---------- | ----------: | ----------- | ---------------------------------------------------------------------------- |
| `mensaje`  |          Sí | -           | Texto enviado por el invitado.                                               |
| `rol`      |          No | `asistente` | Rol lógico de EVA. Actualmente soporta `asistente` y `recepcionista`.        |
| `totem_id` |          No | `default`   | Identificador del tótem o instancia física/visual que está hablando con EVA. |

Si no se envían `rol` ni `totem_id`, el backend usa:

```text
rol=asistente
totem_id=default
```

Esto mantiene compatibilidad con clientes viejos o pruebas rápidas por `curl`.

### Roles disponibles


| Rol             | Uso esperado                                                                                 | Estado actual                                |
| --------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------- |
| `recepcionista` | EVA ubicada en la entrada, orientada a bienvenida, acreditación e ingreso.                   | Usa comportamiento similar al asistente.     |
| `asistente`     | EVA ubicada dentro del evento, orientada a consultas generales, ubicación, agenda y soporte. | Usa comportamiento similar al recepcionista. |

Por ahora ambos roles responden de igual forma. La separación existe a nivel de API y sesiones para que, más adelante, cada rol tenga su propio prompt, reglas de comportamiento, prioridades e intents específicos.

### Historial aislado por sesión

Cada combinación `rol + totem_id` mantiene su propio historial. Esto significa que una conversación en:

```text
recepcionista:totem-A
```

no contamina ni modifica el contexto de:

```text
asistente:totem-2
```

### Ejemplos de uso

#### Chat legacy / default

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"mensaje":"hola"}' | python3 -m json.tool
```

Usa automáticamente:

```text
asistente:default
```

#### Chat con recepcionista

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"mensaje":"hola","rol":"recepcionista","totem_id":"totem-A"}' | python3 -m json.tool
```

Crea o reutiliza la sesión:

```text
recepcionista:totem-A
```

#### Chat con asistente de otro tótem

```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"mensaje":"donde estan los baños?","rol":"asistente","totem_id":"totem-2"}' | python3 -m json.tool
```

Crea o reutiliza la sesión:

```text
asistente:totem-2
```

### Listar sesiones activas

```bash
curl -s http://localhost:8000/sesiones | python3 -m json.tool
```

Respuesta esperada:

```json
{
  "sesiones": [
    {
      "key": "asistente:default",
      "rol": "asistente",
      "historial_length": 2
    },
    {
      "key": "recepcionista:totem-A",
      "rol": "recepcionista",
      "historial_length": 2
    },
    {
      "key": "asistente:totem-2",
      "rol": "asistente",
      "historial_length": 2
    }
  ]
}
```

### Resetear una sesión puntual

El endpoint `/reset` reinicia solo la sesión indicada. No borra todas las sesiones.

```bash
curl -s -X POST "http://localhost:8000/reset?rol=recepcionista&totem_id=totem-A" | python3 -m json.tool
```

Respuesta esperada:

```json
{
  "status": "Sesión 'recepcionista:totem-A' reiniciada, warm-up en proceso"
}
```

Si no se envían parámetros, se resetea la sesión default:

```text
asistente:default
```

```bash
curl -s -X POST http://localhost:8000/reset | python3 -m json.tool
```

### Streaming SSE con sesión

`/chat/stream` acepta los mismos campos que `/chat`:

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"mensaje":"¿Dónde es la acreditación?","rol":"recepcionista","totem_id":"totem-A"}'
```

### Consideraciones para frontend / tótems

Cada tótem debería enviar siempre un `totem_id` fijo y estable. Por ejemplo:

```env
VITE_EVA_ROL=recepcionista
VITE_TOTEM_ID=totem-A
```

o:

```env
VITE_EVA_ROL=asistente
VITE_TOTEM_ID=totem-2
```

El frontend debe incluir esos valores en cada request a `/chat` o `/chat/stream`.

Ejemplo de body enviado por el frontend:

```json
{
  "mensaje": "Hola, ¿dónde me acredito?",
  "rol": "recepcionista",
  "totem_id": "totem-A"
}
```

### Consideraciones para rack / producción

* Varios tótems pueden apuntar al mismo backend.
* Todos los tótems comparten el mismo servicio de Ollama.
* El aislamiento conversacional lo maneja el backend mediante `rol:totem_id`.
* El modelo se carga una sola vez en Ollama.
* Cada sesión mantiene su propio historial en memoria.
* Reiniciar el container del backend borra las sesiones activas en memoria.
* Reiniciar una sesión con `/reset` solo afecta esa combinación puntual de `rol` y `totem_id`.

### Futuro comportamiento por rol

La separación por `rol` ya está implementada para permitir que más adelante cada tipo de EVA tenga comportamiento propio.

Posibles diferencias futuras:

| Rol             | Prompt futuro                                                                                          | Prioridades futuras                                      |
| --------------- | ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------- |
| `recepcionista` | Más orientado a bienvenida, acreditación, ingreso, validación inicial y derivación.                    | Respuestas cortas, ingreso rápido, indicaciones claras.  |
| `asistente`     | Más orientado a orientación dentro del evento, agenda, baños, salones, feedback y consultas generales. | Más contexto del evento, soporte durante la experiencia. |

Cuando se implementen prompts separados, la API no debería cambiar: los clientes seguirán enviando `rol` y `totem_id`.


## Endpoints

### `GET /`
Healthcheck básico.
```bash
curl -s http://localhost:8000/ | python3 -m json.tool
```

### `POST /chat`
Envía un mensaje a EVA. Los campos `rol` y `totem_id` son opcionales — sin
ellos se usa `rol=asistente` y `totem_id=default` (comportamiento de hoy).
Cada combinación `rol + totem_id` mantiene su propia conversación, permitiendo
varios tótems —incluso del mismo rol— corriendo en simultáneo sobre el mismo modelo.
```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"mensaje":"Hola buenas tardes"}' | python3 -m json.tool

# Con rol y tótem explícitos:
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"mensaje":"Hola","rol":"recepcionista","totem_id":"totem-A"}' | python3 -m json.tool
```

### `POST /chat/stream`
Versión streaming SSE usada por el frontend. Acepta los mismos campos
`rol` y `totem_id` que `/chat`.
```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"mensaje":"¿Dónde es la ceremonia?","rol":"asistente","totem_id":"totem-2"}'
```

### `POST /tts`
Convierte texto a WAV con Piper.
```bash
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"texto":"Bienvenido al evento"}' \
  --output salida.wav
```

### `GET /eventos/actual`
Devuelve el evento activo.
```bash
curl -s http://localhost:8000/eventos/actual | python3 -m json.tool
```

### `POST /configure`
Reconfigura EVA en runtime cuando `PROMPT_SOURCE=dynamic`. Invalida todas las
sesiones activas — la próxima vez que cada tótem mande un mensaje, su sesión
se recrea con el prompt nuevo.
```bash
curl -s -X POST http://localhost:8000/configure \
  -H "Content-Type: application/json" \
  -d @mi_evento.json | python3 -m json.tool
```

### `POST /reset`
Reinicia una sesión conversacional puntual. `rol` y `totem_id` van como
query params — sin ellos, resetea `asistente:default`.
```bash
curl -s -X POST http://localhost:8000/reset | python3 -m json.tool

# Resetear solo el recepcionista del tótem A:
curl -s -X POST "http://localhost:8000/reset?rol=recepcionista&totem_id=totem-A" | python3 -m json.tool
```

### `GET /sesiones`
Lista todas las sesiones activas — rol, tótem e historial — útil para
verificar en el día del rack que cada tótem quedó aislado correctamente.
```bash
curl -s http://localhost:8000/sesiones | python3 -m json.tool
```

## Configuración del evento

EVA soporta dos modos de configuración, controlados por `PROMPT_SOURCE`.

### `PROMPT_SOURCE=hardcoded`

Modo recomendado para demo estable. El prompt sale de `app/prompts.py`.

### `PROMPT_SOURCE=dynamic`

El prompt se construye desde un JSON estructurado usando `event_store.py` y `prompt_builder.py`. Permite actualizar el evento con `POST /configure` sin reiniciar el servidor.

---

## Intent matching

EVA detecta intents con embeddings vectoriales:

```text
Mensaje del invitado → nomic-embed-text → vector
Intents conocidos   → nomic-embed-text → vectores indexados al arrancar
Similitud coseno    → intent detectado si supera threshold
```

El código usa Ollama por `OLLAMA_BASE_URL` y el endpoint `/api/embed`.

Para agregar o modificar intents, editar `INTENTS` y `INTENT_THRESHOLDS` en:

```text
app/embeddings.py
```

---

## Feedback

EVA puede detectar feedback con el sistema de embeddings y persistirlo para análisis posterior.

Recomendación para producción:

- persistir archivos en `/app/data`, respaldado por el volumen `sage_data`;
- no escribir datos persistentes dentro de `/app/app`;
- reemplazar el archivo local por una llamada a la API de Analítica cuando esté disponible.

---

## Frontend

El frontend debe apuntar al backend:

```env
VITE_API_PROXY_TARGET=http://localhost:8000
```

Si el frontend corre en un tótem distinto:

```env
VITE_API_PROXY_TARGET=http://IP_DEL_BACKEND:8000
```

Recordar agregar el origen del frontend en `CORS_ORIGINS` del backend. Ejemplo:

```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.1.50:5173
```

Para despliegues con múltiples tótems, el frontend debería tener configurados un rol y un identificador estable de tótem:

```env
VITE_API_PROXY_TARGET=http://IP_DEL_BACKEND:8000
VITE_EVA_ROL=recepcionista
VITE_TOTEM_ID=totem-A
---

## Uso de GPU

El compose incluye configuración base para Ollama y variables como:

```env
NVIDIA_VISIBLE_DEVICES=all
OLLAMA_NUM_PARALLEL=4
```

Para usar GPU en Docker, el host debe tener:

- driver NVIDIA funcionando (`nvidia-smi`);
- NVIDIA Container Toolkit instalado;
- Docker configurado con runtime NVIDIA.

En el rack, revisar `RACK_SETUP.md` antes del deploy.

---

## Troubleshooting

### `sage-agent` no conecta con Ollama

Verificar que dentro de Docker se use:

```env
OLLAMA_BASE_URL=http://ollama:11434
```

No usar `localhost` dentro del container para hablar con Ollama.

Logs:

```bash
docker compose logs -f sage-agent
docker compose logs -f ollama
```

### Error `KeyError: embeddings` o respuesta inesperada de embeddings

Verificar que `app/embeddings.py` use:

```text
/api/embed
```

y que el body use `input`, no `prompt`.

### `/tts` devuelve JSON en vez de WAV

Verificar modelo Piper:

```bash
docker compose exec sage-agent sh -lc '
ls -lah /app/piper/models/
ls -lah /app/piper/models/es_AR-daniela-high.onnx
ls -lah /app/piper/models/es_AR-daniela-high.onnx.json
'
```

Si falta, reconstruir el volumen de Piper:

```bash
docker compose down
docker volume ls | grep piper_models
docker volume rm NOMBRE_DEL_VOLUMEN_PIPER
docker compose up -d
```

### Logs de Ollama tapan los logs del backend

Usar:

```bash
docker compose up -d
docker compose logs -f --tail=100 sage-agent
```

### Compose usa el archivo equivocado

Ejecutar comandos desde la raíz del repo:

```bash
cd ~/sage-agent
```

O pasar el compose explícitamente:

```bash
docker compose -f ~/sage-agent/docker-compose.yml ps
```

### Warning `version is obsolete`

Docker Compose moderno ignora `version:`. Si aparece ese warning, borrar la línea `version:` del compose que se esté usando.

---

## Ejecución local legacy

Esta forma ya no es la intended. Usarla solo para debug puntual.

Requiere instalar manualmente:

- Ollama;
- modelos `llama3.2:3b` y `nomic-embed-text`;
- Piper;
- modelo `es_AR-daniela-high`;
- dependencias Python.

Arranque manual:

```bash
ollama serve &
cd app
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Estructura del proyecto

```text
sage-agent/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
├── RACK_SETUP.md
├── requirements.txt
└── app/
    ├── main.py
    ├── agent.py
    ├── embeddings.py
    ├── prompts.py
    ├── prompt_builder.py
    ├── event_store.py
    ├── feedback.py
    └── test_embeddings.py
```

---

## Próximos pasos técnicos

- [x] Dockerizar backend FastAPI.
- [x] Separar Ollama como servicio Compose.
- [x] Agregar `ollama-init` para descargar modelos automáticamente.
- [x] Agregar `piper-init` para descargar voz Piper automáticamente.
- [x] Usar `/api/embed` para embeddings de Ollama.
- [x] Evitar montar volúmenes sobre `/app/app`.
- [x] Soportar múltiples sesiones conversacionales por `rol:totem_id`.
- [x] Agregar endpoint `GET /sesiones` para debug operativo.
- [x] Permitir reset puntual por `rol` y `totem_id`.
- [ ] Separar prompts específicos para `recepcionista` y `asistente`.
- [ ] Hacer que el frontend envíe `rol` y `totem_id` desde variables de entorno.
- [ ] Persistir o monitorear sesiones si se necesita trazabilidad post-evento.
- [ ] Devolver `500` en `/tts` si Piper falla, no `200` con JSON.
- [ ] Persistir `feedback_log.json` y `current_event.json` en `/app/data`.
- [ ] Validar GPU real en rack con NVIDIA Container Toolkit.
- [ ] Ajustar `CORS_ORIGINS` para IP/dominio final de los tótems.

---

## Equipo

**Responsable del módulo:** Martín  
**PMs:** Lean · Nancy  
**Colaboradores en este módulo:** Mikel · Lucas C · Martu · Nancy
