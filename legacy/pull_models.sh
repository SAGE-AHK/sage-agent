#!/bin/bash
# pull_models.sh — Descargar modelos de Ollama dentro del contenedor
# Correr DESPUÉS de que el servicio ollama esté levantado

echo "[SAGE] Descargando modelos de Ollama..."

docker compose exec ollama ollama pull llama3.2:3b
docker compose exec ollama ollama pull nomic-embed-text

echo "[SAGE] Modelos descargados. Verificando..."
docker compose exec ollama ollama list
