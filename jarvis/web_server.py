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


@app.post("/api/chat")
async def post_chat(body: dict):
    msg = (body.get("message") or "").strip()
    if not msg:
        return {"ok": False, "error": "Leere Nachricht"}
    jarvis_state.message_queue.put(msg)
    return {"ok": True}


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


@app.get("/api/view/file")
async def view_file(path: str):
    from pathlib import Path
    from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse

    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        return JSONResponse({"error": f"Nicht gefunden: {path}"}, status_code=404)

    if p.suffix.lower() == ".pdf":
        return FileResponse(
            str(p), media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )

    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            content = p.read_text(encoding=enc)
            break
        except (UnicodeDecodeError, Exception):
            continue
    else:
        content = p.read_bytes().decode("latin-1", errors="replace")

    return PlainTextResponse(content, media_type="text/plain; charset=utf-8")


@app.get("/api/proxy")
async def proxy_url(url: str):
    import urllib.request
    from fastapi.responses import HTMLResponse

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            ct = resp.headers.get("Content-Type", "text/html")
            charset = "utf-8"
            if "charset=" in ct:
                charset = ct.split("charset=")[-1].split(";")[0].strip()
            html = resp.read().decode(charset, errors="replace")

        base_tag = f'<base href="{url}" target="_blank">'
        if "<head>" in html:
            html = html.replace("<head>", f"<head>\n{base_tag}", 1)
        elif "<HEAD>" in html:
            html = html.replace("<HEAD>", f"<HEAD>\n{base_tag}", 1)
        else:
            html = base_tag + html

        return HTMLResponse(html)
    except Exception as exc:
        return HTMLResponse(
            f'<!DOCTYPE html><html><body style="background:#060d17;color:#7a8a9a;'
            f'font-family:monospace;padding:40px;text-align:center;">'
            f'<div style="color:#e05;font-size:15px;margin-bottom:12px">Fehler beim Laden</div>'
            f'<div style="color:#445;font-size:12px">{exc}</div><br>'
            f'<a href="{url}" target="_blank" style="color:#0cf;font-size:12px">'
            f'Im Browser öffnen ↗</a></body></html>'
        )


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
