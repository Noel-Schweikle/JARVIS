import asyncio
import json
import threading
from collections import deque
from datetime import datetime


class JarvisState:
    def __init__(self):
        self._lock = threading.Lock()
        self.status = "offline"
        self.mode = "text"
        self.current_task = None
        self.start_time = None
        self._activity_counter = 0
        self.activity_log: deque = deque(maxlen=200)
        self.stats = {"total_messages": 0, "total_tool_calls": 0}
        self._ws_clients: set = set()
        self._loop = None

    def set_online(self, mode: str = "text") -> None:
        with self._lock:
            self.status = "idle"
            self.mode = mode
            self.start_time = datetime.now()
            self._activity_counter += 1
            self.activity_log.appendleft({
                "id": self._activity_counter,
                "type": "system",
                "content": f"JARVIS gestartet — Modus: {mode.upper()}",
                "tool": None,
                "timestamp": datetime.now().isoformat(),
            })
        self._broadcast()

    def set_status(self, status: str, task: str = None) -> None:
        with self._lock:
            self.status = status
            self.current_task = task
        self._broadcast()

    def add_activity(self, type_: str, content: str, tool: str = None) -> None:
        with self._lock:
            self._activity_counter += 1
            self.activity_log.appendleft({
                "id": self._activity_counter,
                "type": type_,
                "content": (content or "")[:500],
                "tool": tool,
                "timestamp": datetime.now().isoformat(),
            })
            if type_ == "user":
                self.stats["total_messages"] += 1
            elif type_ == "tool":
                self.stats["total_tool_calls"] += 1
        self._broadcast()

    def register_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def register_ws(self, ws) -> None:
        with self._lock:
            self._ws_clients.add(ws)

    def unregister_ws(self, ws) -> None:
        with self._lock:
            self._ws_clients.discard(ws)

    def get_snapshot(self) -> dict:
        with self._lock:
            uptime = 0.0
            if self.start_time:
                uptime = (datetime.now() - self.start_time).total_seconds()
            return {
                "status": self.status,
                "mode": self.mode,
                "current_task": self.current_task,
                "uptime": uptime,
                "activity_log": list(self.activity_log)[:50],
                "stats": dict(self.stats),
            }

    def _broadcast(self) -> None:
        if not self._loop:
            return
        with self._lock:
            clients = set(self._ws_clients)
        if not clients:
            return
        payload = json.dumps({"type": "state_update", "data": self.get_snapshot()})

        async def _send():
            dead = set()
            for ws in clients:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.add(ws)
            if dead:
                with self._lock:
                    self._ws_clients -= dead

        if self._loop.is_running():
            asyncio.run_coroutine_threadsafe(_send(), self._loop)


jarvis_state = JarvisState()
