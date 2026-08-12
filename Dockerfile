FROM python:3.10-slim

# Install system dependencies (FFmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir flask openai-whisper deep-translator edge-tts

EXPOSE 5000

CMD ["python", "server.py"]