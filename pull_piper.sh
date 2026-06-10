#!/bin/bash
# pull_piper.sh — Descargar modelo de voz Daniela en el volumen de Piper
# Correr DESPUÉS de que el servicio sage-agent esté levantado

echo "[SAGE] Descargando modelo de voz Daniela..."

docker compose exec sage-agent mkdir -p /app/piper/models

docker compose exec sage-agent wget -q \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high/es_AR-daniela-high.onnx \
    -O /app/piper/models/es_AR-daniela-high.onnx

docker compose exec sage-agent wget -q \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high/es_AR-daniela-high.onnx.json \
    -O /app/piper/models/es_AR-daniela-high.onnx.json

echo "[SAGE] Modelo de voz descargado."
docker compose exec sage-agent ls -lh /app/piper/models/
