# EVA — Asistente Virtual de Recepción
### Proyecto SAGE · AHK 2026

EVA es el módulo de asistente conversacional del sistema SAGE. Se encarga de recibir invitados, dar indicaciones dentro del evento y recopilar feedback, utilizando un modelo de lenguaje local sin depender de APIs externas.

---

## Stack

| Componente | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.10+ |
| Framework API | FastAPI | 0.100+ |
| Servidor ASGI | Uvicorn | 0.20+ |
| Modelo LLM | Ollama | latest |
| Modelo de lenguaje | llama3.2:3b | — |
| Entorno recomendado | WSL2 + Ubuntu | Ubuntu 22.04+ |

---

## Requisitos previos

### Windows
- Windows 10/11 con WSL2 habilitado
- Ubuntu instalado en WSL2

### Habilitar WSL2 (si no está instalado)
Desde PowerShell como administrador:
```powershell
wsl --install -d Ubuntu
```

---

## Instalación

### 1. Clonar el repositorio
Desde la terminal de Ubuntu:
```bash
git clone <url-del-repo>
cd sage-agent
```

### 2. Instalar dependencias del sistema
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip curl zstd
```

### 3. Instalar Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Verificar instalación:
```bash
ollama --version
```

### 4. Descargar el modelo de lenguaje
```bash
ollama pull llama3.2:3b
```

> El modelo pesa aproximadamente 2GB. Solo se descarga una vez.

### 5. Instalar dependencias de Python
```bash
pip3 install fastapi uvicorn requests --break-system-packages
```

---

## Configuración del evento

Editá los datos del evento en `app/main.py`:

```python
agent = SageAgent(
    event_name="Nombre del evento",
    event_location="Ubicación del venue",
    event_date="Fecha del evento"
)
```

La información del venue (baños, salidas de emergencia, salón principal, etc.) se configura en `app/prompts.py`.

---

## Correr el servidor

### 1. Iniciar Ollama
```bash
ollama serve &
```

### 2. Iniciar la API
```bash
cd app
python3 -m uvicorn main:app --reload --port 8000
```

Cuando veas `[EVA] Warm-up completado. Modelo listo.` en los logs, el servidor está listo para recibir requests.

---

## Endpoints

### `GET /`
Verifica que el servidor está online.
```bash
curl http://localhost:8000/
# {"status": "EVA online"}
```

### `POST /chat`
Envía un mensaje a EVA y recibe una respuesta.
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"mensaje": "Hola buenas tardes"}'
```
Respuesta:
```json
{
  "respuesta": "¡Buenas tardes! Bienvenido al evento...",
  "historial_length": 2
}
```

### `POST /reset`
Reinicia la sesión conversacional e inicia un nuevo warm-up en background.
```bash
curl -X POST http://localhost:8000/reset
# {"status": "Sesión reiniciada, warm-up en proceso"}
```

---

## Feedback

EVA detecta automáticamente cuando un invitado deja feedback y lo persiste en `app/feedback_log.json`.

Cada entrada registra:
- `id` — identificador único del registro
- `session_id` — identificador de la sesión conversacional
- `timestamp` — fecha y hora del mensaje
- `mensaje_invitado` — texto original del invitado
- `respuesta_eva` — respuesta generada por EVA
- `categoria` — ceremonia / organización / recepción / catering / general
- `sentimiento` — positivo / negativo / neutro

> En la versión de producción este archivo será reemplazado por un endpoint hacia PostgreSQL, coordinado con el equipo de Analítica.

---

## Estructura del proyecto
---

## Dependencias entre equipos

| Lo que necesita EVA | Equipo responsable | Prioridad |
|---|---|---|
| `GET /eventos/:id` — datos del evento dinámicos | Back (Leo, Guille) | Alta |
| `GET /invitados/:qr` — datos del invitado por QR | Back (Santi, Joaco T) | Alta |
| Schema de feedback para PostgreSQL | Analítica (Mati, Luca) | Media |
| Decisión React Native vs PWA para el front | UI/UX (Joaco A, Nancy) | Media |

---

## Próximos pasos del módulo

- [ ] Integración STT (Whisper.cpp) para input por voz
- [ ] Integración TTS (Piper) para respuesta por voz
- [ ] Reemplazar feedback_log.json por endpoint PostgreSQL
- [ ] Endpoint de bienvenida personalizada por QR
- [ ] Integración con API de eventos del equipo back

---

## Equipo

**Responsable del módulo:** Martín  
**PMs:** Lean · Nancy  
**Colaboradores en este módulo:** Mikel · Lucas C · Martu · Nancy
