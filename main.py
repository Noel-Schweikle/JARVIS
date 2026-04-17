#!/usr/bin/env python3
import argparse
import sys
from rich.console import Console

console = Console()


def check_config() -> bool:
    import config
    if not config.OPENAI_API_KEY:
        console.print("[red]Fehler: OPENAI_API_KEY fehlt. Bitte .env Datei anlegen (siehe .env.example)[/red]")
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="JARVIS — KI-Assistent für CAD, PCB & Programmierung"
    )
    parser.add_argument(
        "--voice", action="store_true",
        help="Spracheingabe per Mikrofon (Whisper)",
    )
    parser.add_argument(
        "--speak", action="store_true",
        help="Sprachausgabe aktivieren (OpenAI TTS)",
    )
    args = parser.parse_args()

    if not check_config():
        sys.exit(1)

    from jarvis import agent

    if args.voice:
        agent.run_voice(voice_output=args.speak)
    else:
        agent.run(voice_output=args.speak)


if __name__ == "__main__":
    main()
