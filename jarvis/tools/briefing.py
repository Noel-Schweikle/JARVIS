"""Daily Morning Briefing: Kalender + Wetter + News."""
import json
import urllib.request
import urllib.parse
import urllib.error
import re
from datetime import date


def _weather(city: str = "Munich") -> str:
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        cur = data["current_condition"][0]
        desc = cur["weatherDesc"][0]["value"]
        temp_c = cur["temp_C"]
        feels = cur["FeelsLikeC"]
        humidity = cur["humidity"]
        today = data["weather"][0]
        max_c = today["maxtempC"]
        min_c = today["mintempC"]
        return (
            f"**Wetter {city}:** {desc}, {temp_c}°C (gefühlt {feels}°C)\n"
            f"  Heute: {min_c}°C – {max_c}°C, Luftfeuchtigkeit {humidity}%"
        )
    except Exception as e:
        return f"Wetter nicht verfügbar: {e}"


def _news(topic: str, max_results: int = 3) -> str:
    try:
        from jarvis.tools.web_search import search
        return search(topic, max_results=max_results)
    except Exception as e:
        return f"News nicht verfügbar: {e}"


def _calendar_today() -> str:
    try:
        from jarvis.tools.google_calendar import list_events
        return list_events(max_results=8)
    except Exception as e:
        return f"Kalender nicht verfügbar: {e}"


def _todos_today() -> str:
    try:
        from jarvis.tools.todo import list_tasks
        return list_tasks(filter="hoch")
    except Exception as e:
        return f"Todos nicht verfügbar: {e}"


def morning_briefing(city: str = "Munich") -> str:
    """
    Erstellt das tägliche Morning Briefing:
    Wetter, Kalendertermine, News (3D-Druck + Startups), offene hochprioritäre Todos.
    """
    today_str = date.today().strftime("%A, %d. %B %Y")

    sections: list[str] = [f"# ☀️ JARVIS Morning Briefing — {today_str}\n"]

    # Wetter
    sections.append("## 🌤 Wetter")
    sections.append(_weather(city))
    sections.append("")

    # Kalender
    sections.append("## 📅 Heutige Termine")
    sections.append(_calendar_today())
    sections.append("")

    # Hochprioritäre Todos
    sections.append("## ✅ Offene Aufgaben (Priorität: Hoch)")
    sections.append(_todos_today())
    sections.append("")

    # News: 3D-Druck
    sections.append("## 🖨 News: 3D-Druck")
    sections.append(_news("3D printing industry news today", max_results=3))
    sections.append("")

    # News: Startups
    sections.append("## 🚀 News: Startups & Tech")
    sections.append(_news("startup tech news today", max_results=3))
    sections.append("")

    sections.append("---\n*Guten Morgen! Was sind deine Ziele für heute?*")
    return "\n".join(sections)
