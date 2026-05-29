#!/bin/bash

echo "[SAGE] Iniciando entorno..."

# Iniciar Ollama si no está corriendo
if ! pgrep -x "ollama" > /dev/null; then
    echo "[SAGE] Iniciando Ollama..."
    ollama serve &
    sleep 2
else
    echo "[SAGE] Ollama ya está corriendo."
fi

# Iniciar el servidor
echo "[SAGE] Iniciando EVA en http://localhost:8000"
cd "$(dirname "$0")/app"
python3 -m uvicorn main:app --reload --port 8000
