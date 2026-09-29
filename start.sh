#!/bin/bash
# Build and start the full SpeechMate stack (Postgres, backend, frontend).
set -e
cd "$(dirname "$0")"

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "Created backend/.env from the example — add your API keys there (all optional)."
fi

# Start the bundled local AI servers the backend is configured to use
PROFILE=()
if grep -qE '^LLM_BASE_URL=http://ollama:11434' backend/.env; then
  PROFILE+=(--profile ollama)
  echo "Local LLM: starting Ollama (models download on first run — follow with: docker compose logs -f ollama-pull)"
fi
if grep -qE '^TTS_BASE_URL=http://kokoro:8880' backend/.env; then
  PROFILE+=(--profile tts)
  echo "Local TTS: starting Kokoro (natural voice for the live AI partner)"
fi

echo "Starting SpeechMate via Docker Compose…"
docker compose "${PROFILE[@]}" up --build -d

echo ""
echo "🚀 Services are starting in the background!"
echo "• Frontend:    http://localhost:3000"
echo "• Backend API: http://localhost:8000  (interactive docs: http://localhost:8000/docs)"
echo "• Health:      http://localhost:8000/health  (shows which AI models/providers are active)"
echo ""
echo "Logs: docker compose logs -f     Stop: docker compose ${PROFILE[*]} down"
