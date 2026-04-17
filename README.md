# JARVIS

KI-Assistent für CAD-Konstruktion, PCB-Design und Programmierung.

## Features

- **Sprach- & Texteingabe** — Whisper (OpenAI) für Spracherkennung
- **Sprach- & Textausgabe** — OpenAI TTS mit wählbarer Stimme
- **GitHub** — Dateien lesen & schreiben (Lese-/Schreibrechte)
- **Notion** — Notizen suchen, lesen & erstellen
- **Fusion 360** — Python-Skripte für die Fusion 360 API generieren
- **KiCad / PCB** — KiCad Python-Skripte generieren

## Setup

```bash
# 1. Abhängigkeiten installieren
pip install -r requirements.txt

# 2. .env Datei anlegen
cp .env.example .env
# .env mit API-Keys befüllen

# 3. Starten
python main.py                  # Texteingabe
python main.py --speak          # Texteingabe + Sprachausgabe
python main.py --voice          # Spracheingabe + Textausgabe
python main.py --voice --speak  # Vollständiger Sprachmodus
```

## Konfiguration (.env)

| Variable | Beschreibung |
|---|---|
| `OPENAI_API_KEY` | OpenAI API Key (erforderlich) |
| `GITHUB_TOKEN` | GitHub Personal Access Token (repo-Rechte) |
| `GITHUB_REPO` | Standard-Repository z.B. `noel/jarvis` |
| `NOTION_TOKEN` | Notion Integration Token |
| `NOTION_DATABASE_ID` | Notion Datenbank-ID für neue Seiten |
| `TTS_VOICE` | Stimme: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer` |

## GitHub Token erstellen

1. GitHub → Settings → Developer settings → Personal access tokens
2. Scopes: `repo` (Lesen + Schreiben)

## Notion Token erstellen

1. [notion.so/my-integrations](https://www.notion.so/my-integrations) → New integration
2. Integration in gewünschter Datenbank teilen (Share → Invite)

## Fusion 360 Hinweis

Generierte Skripte müssen in Fusion 360 ausgeführt werden:
- **Scripts**: Tools → Add-Ins → Scripts → Run
- **Add-Ins**: Tools → Add-Ins → My Add-Ins

## Architektur

```
main.py              — Einstiegspunkt & CLI-Argumente
config.py            — Umgebungsvariablen laden
jarvis/
  agent.py           — Konversations-Loop & Tool-Orchestrierung
  voice.py           — Spracheingabe (Whisper) & Sprachausgabe (TTS)
  tools/
    __init__.py      — Tool-Registry & Dispatcher
    github.py        — GitHub API Integration
    notion.py        — Notion API Integration
```
