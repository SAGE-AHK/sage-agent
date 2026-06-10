FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# Instalar Piper TTS
RUN mkdir -p /app/piper && \
    wget -q https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz \
        -O /tmp/piper.tar.gz && \
    tar -xzf /tmp/piper.tar.gz -C /app/piper && \
    rm /tmp/piper.tar.gz

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la aplicación
COPY app/ ./app/

# Variables de entorno por defecto
ENV PIPER_BIN=/app/piper/piper/piper
ENV PIPER_MODEL=/app/piper/models/es_AR-daniela-high.onnx
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV START_OLLAMA=false
ENV OLLAMA_BASE_URL=http://ollama:11434

EXPOSE 8000

WORKDIR /app/app
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
