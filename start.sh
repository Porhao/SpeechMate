#!/bin/bash
# Build and start the full SpeechMate stack (Postgres, backend, frontend).
set -e
cd "$(dirname "$0")"

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "Created backend/.env from the example — add your API keys there (all optional)."
fi

echo "Starting SpeechMate via Docker Compose…"
docker compose up --build -d

echo ""
echo "🚀 Services are starting in the background!"
echo "• Frontend:    http://localhost:3000"
echo "• Backend API: http://localhost:8000  (interactive docs: http://localhost:8000/docs)"
echo "• Health:      http://localhost:8000/health  (shows which AI models/providers are active)"
echo ""
echo "Logs: docker compose logs -f     Stop: docker compose down"
