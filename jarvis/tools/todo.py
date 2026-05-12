"""Lokale Todo-Liste mit JSON-Speicherung (~/.jarvis/todos.json)."""
import json
import os
import uuid
from datetime import datetime
from typing import Optional

_STORAGE_DIR = os.path.expanduser("~/.jarvis")
_STORAGE_FILE = os.path.join(_STORAGE_DIR, "todos.json")

PRIORITIES = {"hoch", "mittel", "niedrig"}


def _load() -> list[dict]:
    if not os.path.exists(_STORAGE_FILE):
        return []
    with open(_STORAGE_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(todos: list[dict]) -> None:
    os.makedirs(_STORAGE_DIR, exist_ok=True)
    with open(_STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


# ── Public API ────────────────────────────────────────────────────────────────

def add_task(
    title: str,
    priority: str = "mittel",
    deadline: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """Fügt eine neue Aufgabe hinzu."""
    if priority not in PRIORITIES:
        priority = "mittel"
    todos = _load()
    task = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "priority": priority,
        "deadline": deadline,
        "notes": notes or "",
        "done": False,
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    todos.append(task)
    _save(todos)
    deadline_str = f", Deadline: {deadline}" if deadline else ""
    return f"✅ Aufgabe erstellt [ID: {task['id']}] — {title} (Priorität: {priority}{deadline_str})"


def list_tasks(filter: str = "offen") -> str:
    """
    Listet Aufgaben auf.
    filter: 'offen' | 'erledigt' | 'alle' | 'hoch' | 'mittel' | 'niedrig'
    """
    todos = _load()
    if not todos:
        return "Keine Aufgaben vorhanden."

    if filter == "offen":
        items = [t for t in todos if not t["done"]]
    elif filter == "erledigt":
        items = [t for t in todos if t["done"]]
    elif filter in PRIORITIES:
        items = [t for t in todos if not t["done"] and t["priority"] == filter]
    else:
        items = todos

    if not items:
        return f"Keine Aufgaben für Filter '{filter}'."

    _priority_icon = {"hoch": "🔴", "mittel": "🟡", "niedrig": "🟢"}
    lines = [f"**Todo-Liste ({filter}) — {len(items)} Aufgabe(n)**\n"]
    for t in sorted(items, key=lambda x: (x["done"], {"hoch": 0, "mittel": 1, "niedrig": 2}.get(x["priority"], 9))):
        status = "☑" if t["done"] else "☐"
        icon = _priority_icon.get(t["priority"], "⚪")
        deadline_str = f" | Deadline: {t['deadline']}" if t.get("deadline") else ""
        notes_str = f"\n    📝 {t['notes']}" if t.get("notes") else ""
        lines.append(f"{status} [{t['id']}] {icon} **{t['title']}**{deadline_str}{notes_str}")

    return "\n".join(lines)


def complete_task(task_id: str) -> str:
    """Markiert eine Aufgabe als erledigt."""
    todos = _load()
    for t in todos:
        if t["id"] == task_id:
            if t["done"]:
                return f"Aufgabe [{task_id}] war bereits erledigt."
            t["done"] = True
            t["completed_at"] = datetime.now().isoformat(timespec="seconds")
            _save(todos)
            return f"✅ Aufgabe [{task_id}] '{t['title']}' als erledigt markiert."
    return f"Aufgabe mit ID '{task_id}' nicht gefunden."


def delete_task(task_id: str) -> str:
    """Löscht eine Aufgabe dauerhaft."""
    todos = _load()
    before = len(todos)
    todos = [t for t in todos if t["id"] != task_id]
    if len(todos) == before:
        return f"Aufgabe mit ID '{task_id}' nicht gefunden."
    _save(todos)
    return f"🗑 Aufgabe [{task_id}] gelöscht."


def update_task(
    task_id: str,
    title: Optional[str] = None,
    priority: Optional[str] = None,
    deadline: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """Aktualisiert eine bestehende Aufgabe."""
    todos = _load()
    for t in todos:
        if t["id"] == task_id:
            if title:
                t["title"] = title
            if priority and priority in PRIORITIES:
                t["priority"] = priority
            if deadline is not None:
                t["deadline"] = deadline
            if notes is not None:
                t["notes"] = notes
            _save(todos)
            return f"✏️ Aufgabe [{task_id}] aktualisiert: {t['title']}"
    return f"Aufgabe mit ID '{task_id}' nicht gefunden."
