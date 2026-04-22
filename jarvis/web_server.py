import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from jarvis.state import jarvis_state

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="JARVIS Dashboard", docs_url=None, redoc_url=None)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/status")
async def get_status():
    return jarvis_state.get_snapshot()


@app.get("/api/calendar")
async def get_calendar():
    try:
        from googleapiclient.discovery import build
        from jarvis.tools.google_auth import get_credentials

        svc = build("calendar", "v3", credentials=get_credentials())
        now = datetime.now(timezone.utc).isoformat()
        result = (
            svc.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=12,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = [
            {
                "id": e["id"],
                "summary": e.get("summary", "(kein Titel)"),
                "start": e["start"].get("dateTime", e["start"].get("date", "")),
                "end": e["end"].get("dateTime", e["end"].get("date", "")),
                "description": e.get("description", ""),
                "location": e.get("location", ""),
            }
            for e in result.get("items", [])
        ]
        return {"success": True, "events": events}
    except Exception as exc:
        return {"success": False, "error": str(exc), "events": []}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    jarvis_state.register_ws(websocket)
    try:
        await websocket.send_text(
            __import__("json").dumps(
                {"type": "state_update", "data": jarvis_state.get_snapshot()}
            )
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        jarvis_state.unregister_ws(websocket)


def start_server(host: str = "127.0.0.1", port: int = 7777) -> threading.Thread:
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        jarvis_state.register_loop(loop)
        cfg = uvicorn.Config(
            app, host=host, port=port, loop="asyncio", log_level="warning"
        )
        server = uvicorn.Server(cfg)
        loop.run_until_complete(server.serve())

    t = threading.Thread(target=_run, daemon=True, name="jarvis-webserver")
    t.start()
    return t
