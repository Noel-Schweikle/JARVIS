import asyncio
import base64
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import config
from jarvis.state import jarvis_state

logger = logging.getLogger(__name__)
REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
BRAIN_DIR = Path.home() / ".jarvis" / "brain"

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


@app.post("/api/brain/upload")
async def brain_upload(file: UploadFile = File(...)):
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    # Dateiname sicher machen
    safe_name = Path(file.filename).name
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._- ()[]").strip()
    if not safe_name:
        safe_name = "unnamed"
    dest = BRAIN_DIR / safe_name
    # Bei Namenskonflikt Suffix anhängen
    if dest.exists():
        stem, suffix = dest.stem, dest.suffix
        i = 1
        while dest.exists():
            dest = BRAIN_DIR / f"{stem}_{i}{suffix}"
            i += 1
    content = await file.read()
    dest.write_bytes(content)
    size_str = f"{len(content) // 1024} KB" if len(content) >= 1024 else f"{len(content)} B"
    return JSONResponse({"ok": True, "name": dest.name, "size": size_str})


@app.get("/api/brain/list")
async def brain_list():
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        [f for f in BRAIN_DIR.iterdir() if f.is_file() and not f.name.startswith(".")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return JSONResponse({
        "files": [
            {
                "name": f.name,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            }
            for f in files
        ]
    })


@app.delete("/api/brain/file")
async def brain_delete(name: str):
    path = BRAIN_DIR / Path(name).name
    if not path.exists():
        return JSONResponse({"ok": False, "error": "Nicht gefunden"}, status_code=404)
    path.unlink()
    return JSONResponse({"ok": True})


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


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """Relay browser mic audio ↔ OpenAI Realtime API.

    Browser sends: binary PCM16 chunks (24 kHz mono)
    Server sends:  JSON text frames
      {"type":"audio","data":"<base64 PCM16>"}  — play this
      {"type":"speech_started"}
      {"type":"speech_stopped"}
      {"type":"transcript_delta","text":"..."}  — live streaming text
      {"type":"user_transcript","text":"..."}   — finalized user turn
      {"type":"jarvis_transcript","text":"..."}  — finalized JARVIS turn
      {"type":"done"}
      {"type":"error","message":"..."}
    """
    await websocket.accept()

    import websockets as _ws

    def _realtime_tools():
        from jarvis.tools import TOOL_SCHEMAS
        result = []
        for s in TOOL_SCHEMAS:
            if s.get("type") == "function":
                f = s["function"]
                result.append({
                    "type": "function",
                    "name": f["name"],
                    "description": f.get("description", ""),
                    "parameters": f.get("parameters", {}),
                })
        return result

    def _system_prompt():
        try:
            from jarvis.agent import _load_system_prompt
            return _load_system_prompt()
        except Exception:
            return "Du bist JARVIS, ein persönlicher KI-Assistent. Antworte immer auf Deutsch."

    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }

    try:
        async with _ws.connect(REALTIME_URL, additional_headers=headers) as oai:
            # Configure Realtime session
            await oai.send(json.dumps({
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": _system_prompt(),
                    "voice": config.TTS_VOICE if config.TTS_VOICE in ("alloy","ash","ballad","coral","echo","sage","shimmer","verse") else "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {"model": "whisper-1"},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 600,
                    },
                    "tools": _realtime_tools(),
                    "tool_choice": "auto",
                },
            }))

            _transcript_buf = []

            async def _from_openai():
                from jarvis.tools import execute_tool
                async for raw in oai:
                    msg = json.loads(raw)
                    t = msg.get("type", "")

                    if t == "input_audio_buffer.speech_started":
                        await websocket.send_json({"type": "speech_started"})

                    elif t == "input_audio_buffer.speech_stopped":
                        await websocket.send_json({"type": "speech_stopped"})

                    elif t == "conversation.item.input_audio_transcription.completed":
                        text = msg.get("transcript", "").strip()
                        if text:
                            jarvis_state.add_activity("user", text)
                            await websocket.send_json({"type": "user_transcript", "text": text})

                    elif t == "response.audio.delta":
                        audio_b64 = msg.get("delta", "")
                        if audio_b64:
                            await websocket.send_json({"type": "audio", "data": audio_b64})

                    elif t == "response.audio_transcript.delta":
                        delta = msg.get("delta", "")
                        _transcript_buf.append(delta)
                        await websocket.send_json({"type": "transcript_delta", "text": delta})

                    elif t == "response.audio_transcript.done":
                        full = msg.get("transcript", "".join(_transcript_buf)).strip()
                        _transcript_buf.clear()
                        if full:
                            jarvis_state.add_activity("assistant", full)
                        await websocket.send_json({"type": "jarvis_transcript", "text": full})

                    elif t == "response.function_call_arguments.done":
                        call_id = msg.get("call_id", "")
                        name = msg.get("name", "")
                        try:
                            args = json.loads(msg.get("arguments", "{}"))
                        except Exception:
                            args = {}
                        jarvis_state.add_activity("tool", str(args)[:200], tool=name)
                        result = execute_tool(name, args)
                        await oai.send(json.dumps({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": call_id,
                                "output": str(result),
                            },
                        }))
                        await oai.send(json.dumps({"type": "response.create"}))

                    elif t == "response.done":
                        await websocket.send_json({"type": "done"})

                    elif t == "error":
                        logger.error("Realtime API error: %s", msg)
                        await websocket.send_json({"type": "error", "message": str(msg.get("error", {}))})

            async def _from_browser():
                while True:
                    try:
                        data = await websocket.receive()
                    except WebSocketDisconnect:
                        break
                    if "bytes" in data and data["bytes"]:
                        await oai.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": base64.b64encode(data["bytes"]).decode(),
                        }))
                    elif "text" in data:
                        try:
                            cmd = json.loads(data["text"])
                            if cmd.get("type") == "commit":
                                await oai.send(json.dumps({"type": "input_audio_buffer.commit"}))
                                await oai.send(json.dumps({"type": "response.create"}))
                        except Exception:
                            pass

            done, pending = await asyncio.wait(
                [asyncio.create_task(_from_openai()), asyncio.create_task(_from_browser())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

    except Exception as exc:
        logger.exception("Voice WebSocket error")
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass


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
