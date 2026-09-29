FROM python:3.12-slim

# LibreOffice + poppler: .pptx → PDF → PNG slide rendering
# ffmpeg: audio normalization, silence detection, video assembly
# espeak-ng: offline TTS fallback when no AI voice provider is configured
# fonts: metric-compatible substitutes for Calibri/Cambria/Arial so decks render faithfully
# libgl1 / libglib2.0-0: runtime libraries MediaPipe/OpenCV need (only used with INSTALL_ML)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-impress \
    poppler-utils \
    ffmpeg \
    espeak-ng \
    fonts-dejavu \
    fonts-liberation \
    fonts-crosextra-carlito \
    fonts-crosextra-caladea \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Local models for live-session analysis (faster-whisper, Wav2Vec2, MediaPipe…).
# Adds ~2 GB; build with --build-arg INSTALL_ML=false for a slim image.
ARG INSTALL_ML=true
RUN if [ "$INSTALL_ML" = "true" ]; then pip install --no-cache-dir -r requirements-ml.txt; fi

COPY . .

RUN mkdir -p /app/storage

EXPOSE 8000
# Migrations, then demo accounts (only when SEED_DEMO_DATA=true), then the API
CMD ["sh", "-c", "alembic upgrade head && python scripts/seed_demo.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
