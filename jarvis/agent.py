import json
import os
import select
import sys
from typing import Optional
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
import config
from jarvis.tools import TOOL_SCHEMAS, execute_tool
from jarvis.state import jarvis_state


def _next_input(prompt: str = "Du: ") -> Optional[str]:
    """Read from web-UI queue OR stdin, whichever arrives first (100 ms polling)."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    while True:
        # Web-UI message has priority
        try:
            msg = jarvis_state.message_queue.get_nowait()
            sys.stdout.write(f"[Web] {msg}\n")
            sys.stdout.flush()
            return msg
        except Exception:
            pass
        # Non-blocking stdin check
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        if ready:
            return sys.stdin.readline().rstrip("\n")

console = Console()

_BASE_SYSTEM = """\
Du bist JARVIS, ein KI-Assistent spezialisiert auf Ingenieur- und Entwickleraufgaben.

## Fähigkeiten

**CAD (Fusion 360)**
- Python-Skripte für die Fusion 360 API (adsk.fusion, adsk.core) schreiben
- Parametrische Modelle, Extrusion, Revolve, Flächen, Körper, Assemblies
- Wichtig: Fusion 360 Skripte laufen als Add-Ins oder Scripts innerhalb von Fusion 360

**PCB-Design (KiCad)**
- KiCad Python-Skripte (pcbnew, schematic) erstellen
- Footprints generieren, DRC-Checks, Netlist-Verarbeitung
- KiCad-Skripte laufen in der KiCad Scripting Console

**Programmierung (via Claude Opus 4.7)**
- Wenn der Nutzer Code programmieren, schreiben, reviewen oder erklären möchte,
  nutze IMMER das Tool `claude_generate_code`, `claude_review_code` oder `claude_explain_code`
- Claude Opus 4.7 ist spezialisiert auf Code — nutze ihn für alle Coding-Aufgaben
- Dateien im GitHub Repository lesen und schreiben

**Web-Recherche**
- Aktuelle Informationen, Fakten und Dokumentationen aus dem Internet suchen (web_search)
- Spezifische Webseiten lesen und zusammenfassen (web_fetch_page)
- Nutze Internetsuche proaktiv wenn aktuelle oder externe Informationen gefragt sind

**Wissensmanagement**
- Notion-Notizen suchen, lesen und erstellen
- Projektdokumentation pflegen

**Google Calendar**
- Termine anzeigen, erstellen und löschen
- Kalender auflisten

**Gmail**
- E-Mails lesen, suchen und senden
- Posteingang filtern (ungelesen, Absender, Betreff)

## Regeln
- Antworte auf Deutsch, Code bleibt auf Englisch
- Frag nach wenn Anforderungen unklar sind
- Teile dem Nutzer mit welche GitHub/Notion-Operationen du durchführst
- Schreibe sauberen, kommentierten Code mit klaren Variablennamen
"""

_VERHALTEN_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "verhalten_gpt.md")


def _load_system_prompt() -> str:
    """Liest verhalten_gpt.md ein und hängt es an den Basis-Prompt an."""
    try:
        with open(_VERHALTEN_PATH, encoding="utf-8") as f:
            verhalten = f.read().strip()
        if verhalten:
            return _BASE_SYSTEM + "\n\n---\n\n" + verhalten
    except FileNotFoundError:
        pass
    return _BASE_SYSTEM


SYSTEM_PROMPT = _load_system_prompt()


def run(voice_output: bool = False) -> None:
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    console.print("[bold green]JARVIS[/bold green] ist bereit.")
    console.print("Befehle: [bold]exit[/bold] beendet, [bold]clear[/bold] löscht Verlauf\n")

    while True:
        try:
            user_input = _next_input("Du: ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Beendet.[/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "beenden"):
            console.print("[dim]Auf Wiedersehen![/dim]")
            break
        if user_input.lower() == "clear":
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            console.print("[dim]Verlauf gelöscht.[/dim]\n")
            continue
        if user_input.lower() == "reload":
            messages = [{"role": "system", "content": _load_system_prompt()}]
            console.print("[dim]Verhalten neu geladen.[/dim]\n")
            continue

        messages.append({"role": "user", "content": user_input})
        jarvis_state.add_activity("user", user_input)
        jarvis_state.set_status("processing", user_input[:80])

        reply = _chat_with_tools(client, messages)
        messages.append({"role": "assistant", "content": reply})
        jarvis_state.add_activity("assistant", reply)
        jarvis_state.set_status("idle")

        console.print("\n[bold green]JARVIS:[/bold green]")
        console.print(Markdown(reply))
        print()

        if voice_output:
            _speak_safe(reply)


def run_voice(voice_output: bool = True) -> None:
    from jarvis import voice as voice_mod

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    console.print("[bold green]JARVIS[/bold green] — Sprachmodus")
    console.print("Enter = Aufnahme starten (5s) | q + Enter = Beenden\n")

    while True:
        try:
            cmd = input("Enter / q: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd == "q":
            break

        try:
            user_input = voice_mod.listen(duration=5)
        except Exception as e:
            console.print(f"[red]Aufnahme-Fehler: {e}[/red]")
            continue

        if not user_input.strip():
            console.print("[dim]Nichts erkannt, bitte erneut versuchen.[/dim]")
            continue

        console.print(f"[bold]Du:[/bold] {user_input}")
        messages.append({"role": "user", "content": user_input})

        reply = _chat_with_tools(client, messages)
        messages.append({"role": "assistant", "content": reply})

        console.print("\n[bold green]JARVIS:[/bold green]")
        console.print(Markdown(reply))
        print()

        if voice_output:
            _speak_safe(reply)


def _chat_with_tools(client: OpenAI, messages: list) -> str:
    while True:
        response = client.chat.completions.create(
            model=config.MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content or ""

        messages.append(msg)

        for call in msg.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments)
            console.print(f"[dim]→ {name}({', '.join(f'{k}={v!r}' for k, v in args.items())})[/dim]")
            jarvis_state.add_activity("tool", str(args)[:200], tool=name)
            result = execute_tool(name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result,
            })


def _speak_safe(text: str) -> None:
    from jarvis import voice as voice_mod
    try:
        voice_mod.speak(text)
    except Exception as e:
        console.print(f"[dim yellow]TTS Fehler: {e}[/dim yellow]")
