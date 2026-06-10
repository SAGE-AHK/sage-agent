# SAGE — Machete del día del rack
### Guía de despliegue de `sage-agent` con Dokploy + Docker Compose

Este documento es la guía operativa para llevar EVA al rack y dejar el backend funcionando para los tótems.

La forma intended de correr `sage-agent` es **Docker Compose**, idealmente gestionado desde **Dokploy**. No preparar el rack instalando Ollama, Piper o dependencias Python a mano salvo para diagnóstico.

---

## Datos conocidos del rack

| Punto | Estado |
|---|---|
| Hardware | 8 cores CPU, 40 GB RAM, 48 GB VRAM total |
| GPUs | 6 GPUs, probablemente 8 GB VRAM cada una |
| Sistema operativo | Ubuntu 24 |
| Conectividad | Ethernet |
| IP | Asignada por DHCP |
| Firewall / puertos | Sin restricciones informadas |
| SSH | Permitido |
| Usuario root/sudo | Accesos provistos por el equipo |
| Instalaciones existentes | Dokploy ya instalado; no tocarlo salvo necesidad |

> Importante: 48 GB VRAM distribuidos en 6 GPUs no es lo mismo que una única GPU de 48 GB. Para la primera prueba, usar un modelo chico/estable (`llama3.2:3b`) y después evaluar modelos más grandes.

---

## Objetivo de arquitectura

```text
Tótem / Frontend 1 ─┐
                    ├── http://IP_DEL_RACK:8000 ── sage-agent ── ollama
Tótem / Frontend 2 ─┘                                  │
                                                       └── Piper TTS
```

Servicios esperados en Docker Compose:

| Servicio | Rol |
|---|---|
| `sage-agent` | API FastAPI de EVA en puerto `8000`. |
| `ollama` | Runtime local de LLM y embeddings. |
| `ollama-init` | Descarga modelos de Ollama y termina. |
| `piper-init` | Descarga modelo/config de voz Piper y termina. |

Puertos:

| Puerto | Uso | Exponer a LAN |
|---|---|---|
| `8000` | Backend EVA | Sí, los tótems lo necesitan. |
| `3000` | Dokploy UI | Sí, para administrar. |
| `11434` | Ollama | Preferentemente no; solo debug o localhost. |

---

## Antes de salir

- [ ] `main` de `sage-agent` commiteado y pusheado.
- [ ] `main` de `sage-agent-front` commiteado y pusheado.
- [ ] Confirmar URL de ambos repositorios.
- [ ] Llevar este archivo actualizado.
- [ ] Llevar `.env` de referencia.
- [ ] Llevar credenciales SSH / Dokploy.
- [ ] Llevar plan B: pendrive con zips de repos, `.env`, y modelos si internet falla.
- [ ] Confirmar cómo se conectan los tótems a la misma red Ethernet/LAN.

---

## 0. Conectarse al rack por SSH

Desde una máquina en la misma red:

```bash
ssh usuario@IP_DEL_RACK
```

Si no sabemos la IP todavía, ver sección siguiente.

Si hay que configurar clave SSH:

```bash
ssh-keygen -t ed25519 -C "sage-ahk"
ssh-copy-id usuario@IP_DEL_RACK
```

---

## 1. Descubrir IP del rack

En el rack:

```bash
hostname -I
ip addr show
ip route
```

Identificar la interfaz Ethernet y la IP asignada por DHCP.

Desde un tótem o laptop:

```bash
ping IP_DEL_RACK
curl http://IP_DEL_RACK:3000
```

### ¿IP estática o DHCP?

Para la primera visita, alcanza con DHCP si la IP no cambia durante la prueba. Para demo/evento real, conviene pedir una de estas opciones:

1. reserva DHCP por MAC address en el router/switch de la red;
2. IP estática configurada en Ubuntu;
3. dominio interno apuntando al rack.

Si se configura IP estática con netplan:

```bash
ip addr show
sudo nano /etc/netplan/00-installer-config.yaml
sudo netplan apply
```

No tocar netplan si no hace falta y la red ya funciona.

---

## 2. Verificar hardware base

```bash
# GPUs
nvidia-smi

# CPU y RAM
nproc
free -h

# Disco
df -h

# SO
lsb_release -a
```

Esperado:

- `nvidia-smi` lista las 6 GPUs;
- RAM cercana a 40 GB;
- Ubuntu 24;
- espacio suficiente en disco para modelos Docker/Ollama.

---

## 3. Verificar Docker, Compose y Dokploy

```bash
docker --version
docker compose version
docker ps
```

Ver Dokploy:

```bash
docker ps | grep -i dokploy
```

Desde browser:

```text
http://IP_DEL_RACK:3000
```

Si Docker no está instalado, instalarlo. Si Dokploy ya está instalado, evitar reinstalar Docker salvo que esté roto.

---

## 4. Verificar GPU en Docker

Aunque `nvidia-smi` funcione en el host, Docker necesita NVIDIA Container Toolkit para que los containers vean las GPUs.

Probar:

```bash
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
```

Si falla, instalar NVIDIA Container Toolkit:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Volver a probar:

```bash
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
```

---

## 5. Revisar `docker-compose.yml` antes del deploy

El compose debe incluir estos servicios:

- `ollama`;
- `ollama-init`;
- `piper-init`;
- `sage-agent`.

Verificar que `sage-agent` no monte `/app/app`:

```yml
volumes:
  - piper_models:/app/piper/models
  - sage_data:/app/data
```

### GPU para Ollama

Para usar GPU en el rack, el servicio `ollama` debería tener reserva de GPU:

```yml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

Si el bloque está comentado, descomentarlo antes de la prueba GPU. Si Dokploy/Compose no lo toma correctamente, validar con logs de Ollama y `nvidia-smi` mientras el modelo responde.

### Puerto de Ollama

Para producción, Ollama no necesita estar expuesto a la LAN. Si solo `sage-agent` le pega internamente, preferir no publicar `11434` o limitarlo:

```yml
ports:
  - "127.0.0.1:11434:11434"
```

El backend sí debe publicar:

```yml
ports:
  - "${API_PORT:-8000}:8000"
```

---

## 6. `.env` recomendado para el rack

Crear/definir variables desde Dokploy o desde `.env`:

```env
API_HOST=0.0.0.0
API_PORT=8000

START_OLLAMA=false

OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_NUM_PARALLEL=4
OLLAMA_REQUEST_TIMEOUT=30

# Reemplazar con URLs/IPs reales de los tótems/frontend.
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://IP_TOTEM_1:5173,http://IP_TOTEM_2:5173

PIPER_BIN=/app/piper/piper/piper
PIPER_MODEL=/app/piper/models/es_AR-daniela-high.onnx

SAGE_DATA_DIR=/app/data
PROMPT_SOURCE=hardcoded
```

Notas:

- `OLLAMA_BASE_URL` debe ser `http://ollama:11434`, no `localhost`.
- `START_OLLAMA=false` porque Ollama corre en su propio container.
- `piper-init` descarga el modelo de voz automáticamente; no correr `pull_piper.sh` salvo que exista un flujo legacy.
- `ollama-init` descarga `OLLAMA_MODEL` y `OLLAMA_EMBED_MODEL`; no correr `pull_models.sh` salvo diagnóstico.

---

## 7. Deploy con Dokploy

Entrar a:

```text
http://IP_DEL_RACK:3000
```

Flujo sugerido:

1. New Project.
2. Elegir Docker Compose.
3. Conectar repositorio `sage-agent`.
4. Seleccionar `docker-compose.yml` de la raíz.
5. Configurar variables de entorno según la sección anterior.
6. Deploy.
7. Abrir logs de `piper-init`, `ollama-init` y `sage-agent`.

Estados esperados:

```text
piper-init   exited 0
ollama-init  exited 0
ollama       running / healthy
sage-agent   running
```

Si `ollama-init` tarda, probablemente esté descargando modelos. Es normal en el primer deploy.

---

## 8. Deploy manual de fallback

Si Dokploy falla, probar directo por SSH:

```bash
git clone <url-sage-agent>
cd sage-agent
cp .env.example .env
nano .env

docker compose up -d --build
docker compose logs -f --tail=100 sage-agent
```

Ver estado:

```bash
docker compose ps
```

Reset completo:

```bash
docker compose down -v
docker compose up -d --build
```

---

## 9. Validación del backend en el rack

Desde el rack:

```bash
curl -s http://localhost:8000/ | python3 -m json.tool
```

Desde una laptop/tótem en la misma red:

```bash
curl -s http://IP_DEL_RACK:8000/ | python3 -m json.tool
```

### Chat

```bash
curl -s -X POST http://IP_DEL_RACK:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"mensaje":"Hola EVA, ¿dónde es la acreditación?"}' | python3 -m json.tool
```

El campo correcto es `mensaje`.

### TTS

```bash
curl -X POST http://IP_DEL_RACK:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"texto":"Hola, soy EVA. Bienvenido al evento."}' \
  --output /tmp/eva_tts.wav

file /tmp/eva_tts.wav
ls -lh /tmp/eva_tts.wav
```

Esperado:

```text
RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, mono 22050 Hz
```

Si dice `JSON text data`, Piper no generó audio. Revisar sección de troubleshooting.

---

## 10. Configurar tótems / frontend

En cada tótem, el frontend debe apuntar al rack:

```env
VITE_API_PROXY_TARGET=http://IP_DEL_RACK:8000
```

Levantar front:

```bash
npm install
npm run dev
```

Abrir:

```text
http://localhost:5173
```

Desde el tótem:

```bash
curl http://IP_DEL_RACK:8000/
```

En el backend, `CORS_ORIGINS` debe incluir el origen real del frontend. Si el tótem corre Vite localmente:

```env
CORS_ORIGINS=http://IP_TOTEM_1:5173,http://IP_TOTEM_2:5173,http://localhost:5173,http://127.0.0.1:5173
```

---

## 11. Medir latencia y GPU

En el frontend, abrir DevTools y mirar logs:

```text
[EVA Latencia] LLM completado: Xms
[EVA Latencia] Piper respuesta recibida: Xms
[EVA Latencia] Audio reproduciéndose: Xms
```

En el rack, mirar uso de GPU mientras EVA responde:

```bash
watch -n 0.5 nvidia-smi
```

Para primera prueba:

```env
OLLAMA_MODEL=llama3.2:3b
OLLAMA_NUM_PARALLEL=4
```

No arrancar directo con `70b`. Primero validar estabilidad, concurrencia y latencia con modelo chico.

---

## 12. Comandos útiles

### Logs limpios del backend

```bash
docker compose logs -f --tail=100 sage-agent
```

### Logs de init

```bash
docker compose logs piper-init
docker compose logs ollama-init
```

### Ver modelos de Ollama

```bash
docker compose exec ollama ollama list
```

### Pull manual de modelo extra

```bash
docker compose exec ollama ollama pull llama3.1:8b
```

Después cambiar:

```env
OLLAMA_MODEL=llama3.1:8b
```

Y redeploy/restart.

### Ver archivos Piper dentro del backend

```bash
docker compose exec sage-agent sh -lc '
ls -lah /app/piper/models/
ls -lah /app/piper/models/es_AR-daniela-high.onnx
ls -lah /app/piper/models/es_AR-daniela-high.onnx.json
'
```

---

## Troubleshooting

### Dokploy levanta pero EVA no responde

Revisar logs de `sage-agent`.

```bash
docker compose logs -f --tail=100 sage-agent
```

Confirmar:

```bash
docker compose ps
```

### `sage-agent` no conecta con Ollama

Verificar `.env`:

```env
OLLAMA_BASE_URL=http://ollama:11434
```

No usar `localhost` dentro de Docker.

Probar desde backend:

```bash
docker compose exec sage-agent sh -lc 'curl -s http://ollama:11434/api/tags | head'
```

### Modelos de Ollama no descargados

Ver logs:

```bash
docker compose logs ollama-init
```

Pull manual:

```bash
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull llama3.2:3b
```

### Piper no encuentra el modelo

Verificar archivos:

```bash
docker compose exec sage-agent sh -lc 'ls -lah /app/piper/models/'
```

Si falta el modelo, resetear solo volumen de Piper:

```bash
docker compose down
docker volume ls | grep piper_models
docker volume rm NOMBRE_DEL_VOLUMEN_PIPER
docker compose up -d
```

Luego:

```bash
docker compose logs piper-init
```

### `/tts` devuelve JSON en vez de WAV

Diagnóstico:

```bash
curl -v -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"texto":"Hola, soy EVA"}' \
  --output /tmp/eva_tts.wav

file /tmp/eva_tts.wav
cat /tmp/eva_tts.wav
```

Si el archivo es JSON, revisar logs de `sage-agent` y `piper-init`.

### Frontend falla por CORS

Error típico en navegador:

```text
blocked by CORS policy
```

Solución: agregar el origen real del frontend en `CORS_ORIGINS` y redeploy.

### Tótem no llega al rack

Desde tótem:

```bash
ping IP_DEL_RACK
curl http://IP_DEL_RACK:8000/
```

En rack:

```bash
ss -ltnp | grep 8000
```

Si hace falta:

```bash
sudo ufw status
sudo ufw allow 8000
```

### Docker no ve GPUs

```bash
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
```

Si falla, revisar NVIDIA Container Toolkit.

### Ollama parece correr en CPU

Revisar logs de Ollama y `nvidia-smi` durante una consulta.

```bash
docker compose logs ollama
watch -n 0.5 nvidia-smi
```

Si no usa GPU:

- confirmar NVIDIA Container Toolkit;
- confirmar bloque `deploy.resources.reservations.devices`;
- confirmar que Dokploy respete esa configuración;
- probar manualmente con `docker compose up` fuera de Dokploy.

### Logs de Ollama son demasiado ruidosos

Para trabajar cómodo:

```bash
docker compose up -d
docker compose logs -f --tail=100 sage-agent
```

En compose, se puede dejar:

```yml
logging:
  driver: "none"
```

para `ollama` y/o `ollama-init`.

---

## Checklist final de validación

### Rack

- [ ] SSH funciona.
- [ ] Dokploy UI accesible en `http://IP_DEL_RACK:3000`.
- [ ] `nvidia-smi` muestra todas las GPUs.
- [ ] Docker funciona.
- [ ] Docker Compose funciona.
- [ ] Docker ve GPUs con `docker run --gpus all ... nvidia-smi`.
- [ ] `sage-agent` deployado desde Dokploy.
- [ ] `ollama-init` terminó con exit `0`.
- [ ] `piper-init` terminó con exit `0`.
- [ ] `sage-agent` está running.
- [ ] `GET /` devuelve `EVA online`.
- [ ] `POST /chat` responde correctamente.
- [ ] `POST /tts` genera WAV válido.

### Tótems

- [ ] Tótem 1 llega a `http://IP_DEL_RACK:8000/`.
- [ ] Tótem 2 llega a `http://IP_DEL_RACK:8000/`.
- [ ] Frontend apunta a `VITE_API_PROXY_TARGET=http://IP_DEL_RACK:8000`.
- [ ] CORS configurado para ambos tótems.
- [ ] STT funciona con micrófono real.
- [ ] TTS reproduce audio real.
- [ ] Dos tótems pueden consultar simultáneamente sin bloquearse.

### Performance

- [ ] Latencia LLM medida.
- [ ] Latencia TTS medida.
- [ ] Uso de GPU observado con `nvidia-smi`.
- [ ] Modelo actual documentado.
- [ ] `OLLAMA_NUM_PARALLEL` documentado.

---

## Pendientes recomendados antes de demo real

- [ ] Devolver `500` en `/tts` si Piper falla, no `200` con JSON.
- [ ] Persistir `feedback_log.json` y `current_event.json` en `/app/data`.
- [ ] Decidir si Ollama queda expuesto o solo interno.
- [ ] Definir IP estática/reserva DHCP del rack.
- [ ] Definir URLs finales del frontend/tótems para `CORS_ORIGINS`.
- [ ] Probar carga con 2 tótems reales.
