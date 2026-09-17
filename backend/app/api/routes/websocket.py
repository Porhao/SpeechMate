import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.utils.security import decode_token

router = APIRouter(tags=["WebSocket"])

active_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/session/{session_id}")
async def session_websocket(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
):
    try:
        payload = decode_token(token)
        user_id = payload["sub"]
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    active_connections.setdefault(session_id, []).append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            # Echo back with processed feedback
            # In production, this routes audio chunks to speech/vision AI
            if msg.get("type") == "audio.chunk":
                await websocket.send_text(json.dumps({
                    "type": "speech.fluency",
                    "data": 78.5,
                }))
                await websocket.send_text(json.dumps({
                    "type": "speech.pronunciation",
                    "data": 82.0,
                }))

            elif msg.get("type") == "video.frame":
                await websocket.send_text(json.dumps({
                    "type": "vision.eyecontact",
                    "data": 75.0,
                }))
                await websocket.send_text(json.dumps({
                    "type": "vision.confidence",
                    "data": 80.0,
                }))

    except WebSocketDisconnect:
        connections = active_connections.get(session_id, [])
        if websocket in connections:
            connections.remove(websocket)
