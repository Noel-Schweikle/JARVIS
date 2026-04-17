import json
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
import config
from jarvis.tools import TOOL_SCHEMAS, execute_tool

console = Console()

SYSTEM_PROMPT = """\
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

**Programmierung**
- Code reviewen, debuggen, refactoren
- Dateien im GitHub Repository lesen und schreiben

**Wissensmanagement**
- Notion-Notizen suchen, lesen und erstellen
- Projektdokumentation pflegen

## Regeln
- Antworte auf Deutsch, Code bleibt auf Englisch
- Frag nach wenn Anforderungen unklar sind
- Teile dem Nutzer mit welche GitHub/Notion-Operationen du durchführst
- Schreibe sauberen, kommentierten Code mit klaren Variablennamen
"""


def run(voice_output: bool = False) -> None:
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    console.print("[bold green]JARVIS[/bold green] ist bereit.")
    console.print("Befehle: [bold]exit[/bold] beendet, [bold]clear[/bold] löscht Verlauf\n")

    while True:
        try:
            user_input = input("Du: ").strip()
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

        messages.append({"role": "user", "content": user_input})
        reply = _chat_with_tools(client, messages)
        messages.append({"role": "assistant", "content": reply})

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
