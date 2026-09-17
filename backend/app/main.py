from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.database.base import create_tables
from app.api.routes import auth, users, practice, speech, vision, coach, reports, websocket, analysis, tts, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 routes
PREFIX = "/api/v1"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(practice.router, prefix=PREFIX)
app.include_router(speech.router, prefix=PREFIX)
app.include_router(vision.router, prefix=PREFIX)
app.include_router(coach.router, prefix=PREFIX)
app.include_router(reports.router, prefix=PREFIX)
app.include_router(analysis.router, prefix=PREFIX)
app.include_router(tts.router, prefix=PREFIX)
app.include_router(chat.router, prefix=PREFIX)

# WebSocket (no prefix — connects at /ws/session/{id})
app.include_router(websocket.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.APP_NAME}
