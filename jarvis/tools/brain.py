"""JARVIS Gehirn — Datei-Wissensbasis in ~/.jarvis/brain/."""
import json
import mimetypes
import os
import re
from datetime import datetime
from pathlib import Path

BRAIN_DIR = Path.home() / ".jarvis" / "brain"


def _ensure_dir() -> None:
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)


def list_files() -> str:
    """Listet alle Dateien im Gehirn auf."""
    _ensure_dir()
    files = sorted(BRAIN_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    files = [f for f in files if f.is_file() and not f.name.startswith(".")]
    if not files:
        return "Das Gehirn ist leer. Dateien per Drag & Drop auf das Dashboard ziehen."
    lines = [f"**Gehirn — {len(files)} Datei(en)**\n"]
    for f in files:
        size = f.stat().st_size
        size_str = f"{size // 1024} KB" if size >= 1024 else f"{size} B"
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
        lines.append(f"• **{f.name}** ({size_str}) — {mtime}")
    return "\n".join(lines)


def read_file(filename: str) -> str:
    """Liest eine Datei aus dem Gehirn und gibt den Inhalt zurück."""
    _ensure_dir()
    path = BRAIN_DIR / Path(filename).name  # Kein path traversal
    if not path.exists():
        available = [f.name for f in BRAIN_DIR.iterdir() if f.is_file()]
        return f"Datei '{filename}' nicht gefunden. Verfügbar: {', '.join(available) or 'keine'}"

    suffix = path.suffix.lower()

    # PDF
    if suffix == ".pdf":
        try:
            import pdfplumber
            lines = []
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages[:20]:
                    t = page.extract_text()
                    if t:
                        lines.append(t)
            text = "\n".join(lines)[:15_000]
            return f"**{filename} (PDF, {len(text)} Zeichen):**\n\n{text}"
        except ImportError:
            pass
        except Exception as e:
            return f"PDF-Lesefehler: {e}"

    # Text-Dateien
    text_suffixes = {".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
                     ".csv", ".html", ".css", ".xml", ".toml", ".ini", ".cfg", ".log",
                     ".c", ".h", ".cpp", ".ino", ".rs", ".go", ".java", ".kt", ".swift"}
    if suffix in text_suffixes or mimetypes.guess_type(str(path))[0] in ("text/plain", "text/csv"):
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                content = path.read_text(encoding=enc)[:15_000]
                return f"**{filename}:**\n\n{content}"
            except UnicodeDecodeError:
                continue
        return f"Datei '{filename}' konnte nicht als Text gelesen werden."

    return f"Datei '{filename}' hat ein nicht lesbares Format ({suffix}). Verfügbar als Download."


def delete_file(filename: str) -> str:
    """Löscht eine Datei aus dem Gehirn."""
    _ensure_dir()
    path = BRAIN_DIR / Path(filename).name
    if not path.exists():
        return f"Datei '{filename}' nicht gefunden."
    path.unlink()
    return f"🗑 '{filename}' aus dem Gehirn gelöscht."


def search_files(query: str) -> str:
    """Durchsucht alle Text-Dateien im Gehirn nach einem Begriff."""
    _ensure_dir()
    query_lower = query.lower()
    results = []
    for path in sorted(BRAIN_DIR.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        matches = [
            line.strip() for line in content.splitlines()
            if query_lower in line.lower()
        ]
        if matches:
            results.append(f"**{path.name}** — {len(matches)} Treffer:")
            for m in matches[:3]:
                results.append(f"  › {m[:120]}")

    if not results:
        return f"Keine Treffer für '{query}' im Gehirn."
    return "\n".join(results)
