#!/bin/bash

# Ensure the backend database file exists to avoid docker creating a directory instead
touch ./backend/speechmate.db

echo "Starting SpeechMate via Docker Compose..."
echo "This will build and start both the Next.js frontend and FastAPI backend."
echo ""

docker compose up --build -d

echo ""
echo "🚀 Services are starting in the background!"
echo "• Frontend will be available at: http://localhost:3000"
echo "• Backend API will be available at: http://localhost:8000"
echo ""
echo "To view logs, run: docker compose logs -f"
echo "To stop services, run: docker compose down"
