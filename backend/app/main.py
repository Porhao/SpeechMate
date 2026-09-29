"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, conversation, health, live, practice, sessions
from app.services import tasks

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# httpx logs every request at INFO, which drowns out pipeline progress
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.secret_key == "change-me-in-production":
        logging.getLogger(__name__).warning("SECRET_KEY is the default — set a real one in .env before deploying")
    await tasks.fail_interrupted_jobs()
    yield
    await tasks.wait_for_all(timeout=10)


app = FastAPI(
    title="SpeechMate",
    description=(
        "AI communication coach for Malaysian speakers. Presentation coaching (an Ideal "
        "Presentation Agent that narrates your deck in your own voice, and a Coach Agent that "
        "gives Observation–Impact–Suggestion feedback), plus live practice sessions with an AI "
        "partner and multimodal speech + vision analysis."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(sessions.router, prefix="/api")
app.include_router(practice.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(live.router, prefix="/api")
app.include_router(conversation.router, prefix="/api")
