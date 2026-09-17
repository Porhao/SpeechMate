# SpeechMate

An AI-powered communication and speech-coaching web app, built as a Final Year Project (FYP), with a specific focus on **Malaysian speakers** — English, Bahasa Malaysia, and the code-switched "Manglish" speech that generic Western speech-coaching tools handle badly.

The core idea: give a user a live practice session (camera + mic), analyse how they spoke and presented afterward across several channels — fluency, pronunciation, disfluency, eye contact, posture, facial emotion — and turn that into a single communication score plus specific, personalised, actionable feedback.

---

## 🌟 What Makes This Different

1. **Accent-fair pronunciation scoring:** Deviations from "standard" pronunciation are split into two buckets: consistent Malaysian-English phonology (regional variation — not penalised) vs. deviations that would actually cost a listener intelligibility (flagged).
2. **"Never interrupts:"** All scoring and correction is held until the user finishes speaking — nothing interrupts mid-sentence to reduce cognitive load and anxiety.
3. **Gaze Tunneling:** A fused metric that computes the real Pearson correlation between gaze aversion and disfluency events over time, rather than just independent eye-contact and disfluency stats.

---

## 🏗️ Architecture

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, Zustand. Uses MediaPipe Tasks Vision client-side for real-time face/pose tracking, Web Audio API, and Web Speech API.
- **Backend:** FastAPI (Python 3.13), SQLAlchemy (SQLite), OpenAI API for coaching chat.
- **AI Pipeline:** Audio/Video → ASR (faster-whisper & wav2vec2-xls-r-300m-mixed for codeswitching) → Speech/Vision Analysis → Scoring → Recommendations.

---

## 🚀 Getting Started

The easiest way to run the project is using Docker Compose, which handles both the frontend and backend services.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed on your machine.

### 1. Environment Setup

The backend requires an OpenAI API key for the coaching chat and feedback generation.

Create a `.env` file in the `backend/` directory:

```bash
# Create the file
touch backend/.env

# Add your OpenAI API key (replace with your actual key)
echo "OPENAI_API_KEY=your_openai_api_key_here" >> backend/.env
```

### 2. Start the Application

You can use the provided start script to build and launch the application:

```bash
# Make the script executable if it isn't already
chmod +x start.sh

# Run the start script
./start.sh
```

Alternatively, you can run Docker Compose directly:

```bash
# Ensure the database file exists first (prevents Docker from creating a directory)
touch ./backend/speechmate.db

# Start services in the background
docker compose up --build -d
```

### 3. Access the Application

Once the services are up and running, they will be available at:

- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Backend API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

### Useful Commands

- **View Logs:** `docker compose logs -f`
- **Stop Services:** `docker compose down`
- **Rebuild Containers (if you change dependencies):** `docker compose build`

---

## 📊 Data Model & Storage

Data is stored locally using SQLite (`backend/speechmate.db`). The schema includes tables for users, profiles, practice sessions, multimodal analysis results (speech & vision), AI feedback, and progress history.

> **Note on Initial Run:** The code-switching ASR model (~1.2GB) is downloaded automatically by the backend on the first non-English transcription rather than being bundled with the Docker image.
