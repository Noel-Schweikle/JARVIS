import json
from jarvis.tools import github, notion

# ── Claude Coding Tools ──────────────────────────────────────────────────────
_CLAUDE_CODING_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "claude_generate_code",
            "description": (
                "Programmiert Code mit Claude Opus 4.7 (Anthropic). "
                "Nutze dieses Tool immer wenn der Nutzer Code programmieren, schreiben oder "
                "erstellen möchte — egal welche Sprache oder Framework."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Was soll programmiert werden? Genaue Beschreibung der Aufgabe.",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programmiersprache oder Framework (z.B. Python, TypeScript, React, Arduino)",
                    },
                    "context": {
                        "type": "string",
                        "description": "Zusätzlicher Kontext, Anforderungen oder bestehender Code",
                    },
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "claude_review_code",
            "description": (
                "Lässt Claude Opus 4.7 Code reviewen, verbessern und Probleme finden. "
                "Nutze dieses Tool wenn der Nutzer Code reviewen, debuggen oder verbessern möchte."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Der zu reviewende Code"},
                    "language": {"type": "string", "description": "Programmiersprache (optional)"},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "claude_explain_code",
            "description": (
                "Lässt Claude Opus 4.7 Code erklären. "
                "Nutze dieses Tool wenn der Nutzer Code erklärt haben möchte."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Der zu erklärende Code"},
                    "language": {"type": "string", "description": "Programmiersprache (optional)"},
                },
                "required": ["code"],
            },
        },
    },
]

TOOL_SCHEMAS = _CLAUDE_CODING_SCHEMAS + [
    # ── GitHub ──────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "github_read_file",
            "description": "Liest eine Datei aus dem GitHub Repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Dateipfad im Repository"},
                    "repo": {"type": "string", "description": "owner/name (optional)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_write_file",
            "description": "Erstellt oder aktualisiert eine Datei im GitHub Repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "message": {"type": "string", "description": "Commit-Nachricht"},
                    "repo": {"type": "string", "description": "owner/name (optional)"},
                },
                "required": ["path", "content", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_list_repos",
            "description": "Listet alle GitHub Repositories des Nutzers auf",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_list_files",
            "description": "Listet Dateien in einem Verzeichnis des GitHub Repositories",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Verzeichnispfad (leer = Root)"},
                    "repo": {"type": "string", "description": "owner/name (optional)"},
                },
                "required": [],
            },
        },
    },
    # ── Notion ───────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "notion_search",
            "description": "Sucht in Notion nach Seiten und Datenbank-Einträgen",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Suchbegriff"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notion_read_page",
            "description": "Liest den vollständigen Inhalt einer Notion-Seite",
            "parameters": {
                "type": "object",
                "properties": {"page_id": {"type": "string", "description": "Notion Page ID"}},
                "required": ["page_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notion_create_page",
            "description": "Erstellt eine neue Seite in der Notion-Datenbank",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string", "description": "Inhalt im Markdown-Format"},
                },
                "required": ["title", "content"],
            },
        },
    },
    # ── Google Calendar ──────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "calendar_list_events",
            "description": "Zeigt bevorstehende Termine aus Google Calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Max. Anzahl Termine (Standard: 10)"},
                    "calendar_id": {"type": "string", "description": "Kalender-ID (Standard: primary)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_create_event",
            "description": "Erstellt einen neuen Termin in Google Calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Titel des Termins"},
                    "start": {"type": "string", "description": "Startzeit ISO-8601, z.B. 2024-06-01T14:00:00+02:00"},
                    "end": {"type": "string", "description": "Endzeit ISO-8601"},
                    "description": {"type": "string", "description": "Beschreibung (optional)"},
                    "location": {"type": "string", "description": "Ort (optional)"},
                    "calendar_id": {"type": "string", "description": "Kalender-ID (Standard: primary)"},
                },
                "required": ["summary", "start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_delete_event",
            "description": "Löscht einen Termin aus Google Calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "Event-ID (aus calendar_list_events)"},
                    "calendar_id": {"type": "string", "description": "Kalender-ID (Standard: primary)"},
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_list_calendars",
            "description": "Listet alle verfügbaren Google Kalender auf",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ── Web-Suche & Fetch ────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Sucht im Internet nach aktuellen Informationen, Fakten, Dokumentationen oder Neuigkeiten. "
                "Nutze dieses Tool wenn der Nutzer etwas recherchieren, nachschlagen oder aktuelle "
                "Informationen aus dem Web benötigt."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Suchanfrage (auf Englisch für beste Ergebnisse)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximale Anzahl Ergebnisse (Standard: 5)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch_page",
            "description": (
                "Lädt den Textinhalt einer bestimmten Webseite. "
                "Nutze dieses Tool um eine spezifische URL zu lesen, z.B. eine Dokumentationsseite "
                "oder einen Artikel aus den Web-Suchergebnissen."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Die vollständige URL der Webseite",
                    },
                },
                "required": ["url"],
            },
        },
    },
    # ── Gehirn (Brain-Dateispeicher) ─────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "brain_list",
            "description": "Listet alle Dateien im JARVIS-Gehirn auf (~/.jarvis/brain/)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "brain_read",
            "description": (
                "Liest eine Datei aus dem JARVIS-Gehirn. Unterstützt Text, Markdown, PDF, Code, CSV etc. "
                "Nutze dieses Tool wenn der Nutzer nach Inhalten einer hochgeladenen Datei fragt."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Dateiname (aus brain_list)"},
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "brain_search",
            "description": "Durchsucht alle Text-Dateien im Gehirn nach einem Suchbegriff",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Suchbegriff"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "brain_delete",
            "description": "Löscht eine Datei aus dem JARVIS-Gehirn",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Dateiname"},
                },
                "required": ["filename"],
            },
        },
    },
    # ── Todo-Liste ───────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "todo_add",
            "description": "Fügt eine neue Aufgabe zur Todo-Liste hinzu",
            "parameters": {
                "type": "object",
                "properties": {
                    "title":    {"type": "string", "description": "Titel der Aufgabe"},
                    "priority": {"type": "string", "description": "'hoch', 'mittel' oder 'niedrig' (Standard: 'mittel')"},
                    "deadline": {"type": "string", "description": "Fälligkeitsdatum ISO-8601, z.B. 2024-06-01 (optional)"},
                    "notes":    {"type": "string", "description": "Zusätzliche Notizen (optional)"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_list",
            "description": "Listet Aufgaben auf. Filter: 'offen', 'erledigt', 'alle', 'hoch', 'mittel', 'niedrig'",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "description": "Filter (Standard: 'offen')"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_complete",
            "description": "Markiert eine Aufgabe als erledigt",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "8-stellige Aufgaben-ID (aus todo_list)"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_delete",
            "description": "Löscht eine Aufgabe dauerhaft",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Aufgaben-ID"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_update",
            "description": "Aktualisiert Titel, Priorität, Deadline oder Notiz einer Aufgabe",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id":  {"type": "string"},
                    "title":    {"type": "string"},
                    "priority": {"type": "string"},
                    "deadline": {"type": "string"},
                    "notes":    {"type": "string"},
                },
                "required": ["task_id"],
            },
        },
    },
    # ── Morning Briefing ─────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "morning_briefing",
            "description": (
                "Erstellt das tägliche Morning Briefing: Wetter, Kalendertermine, "
                "offene hochprioritäre Todos sowie aktuelle News aus der 3D-Druck- und Startup-Branche. "
                "Nutze dieses Tool wenn der Nutzer das Tages-Briefing abruft oder nach dem Tagesplan fragt."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Stadt für Wetterabfrage (Standard: Munich)"},
                },
                "required": [],
            },
        },
    },
    # ── Hardware/Embedded Agent ──────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "hardware_load_datasheet",
            "description": (
                "Lädt ein Bauteil-Datasheet (lokale PDF-Datei oder URL) und extrahiert automatisch "
                "Kennwerte wie Flash, SRAM, Clock, GPIO, ADC, UART, SPI, I2C. "
                "Nutze dieses Tool wenn der Nutzer ein Datasheet hochladen oder ein Bauteil einlesen möchte."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source":         {"type": "string", "description": "Dateipfad oder URL zum PDF"},
                    "component_name": {"type": "string", "description": "Name des Bauteils, z.B. 'ATmega1284P' (optional)"},
                },
                "required": ["source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hardware_query_component",
            "description": (
                "Beantwortet eine Frage zu einem geladenen Bauteil, z.B. 'Wie viel RAM hat der ATmega1284P?' "
                "oder 'Hat der ATmega1284P einen ADC?'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "component_name": {"type": "string", "description": "Bauteilname, z.B. 'ATmega1284P'"},
                    "question":       {"type": "string", "description": "Frage zu den Spezifikationen"},
                },
                "required": ["component_name", "question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hardware_list_components",
            "description": "Listet alle geladenen Bauteile/Datasheets mit ihren extrahierten Kennwerten auf",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hardware_schematic_hints",
            "description": (
                "Gibt Mindest-Schaltplan-Hinweise für ein Bauteil zurück: "
                "Entkopplung, Reset, Taktquelle, Debug-Header etc. "
                "Nutze dieses Tool wenn der Nutzer Hilfe beim Schaltplan-Design benötigt."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "component_name": {"type": "string", "description": "Bauteilname, z.B. 'ATmega1284P' oder 'STM32F103'"},
                },
                "required": ["component_name"],
            },
        },
    },
    # ── Gmail ────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "gmail_list_emails",
            "description": "Listet E-Mails aus dem Gmail-Postfach auf",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Max. Anzahl E-Mails (Standard: 10)"},
                    "query": {"type": "string", "description": "Gmail-Suchfilter, z.B. 'is:unread' oder 'from:chef@firma.de'"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_read_email",
            "description": "Liest den vollständigen Inhalt einer E-Mail",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "E-Mail ID (aus gmail_list_emails)"}
                },
                "required": ["message_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_send_email",
            "description": "Sendet eine E-Mail über Gmail",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Empfänger-E-Mail-Adresse"},
                    "subject": {"type": "string", "description": "Betreff"},
                    "body": {"type": "string", "description": "E-Mail-Text"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_search_emails",
            "description": "Sucht E-Mails nach Gmail-Suchsyntax (z.B. 'from:name@example.com subject:Rechnung')",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail-Suchanfrage"},
                    "max_results": {"type": "integer", "description": "Max. Treffer (Standard: 10)"},
                },
                "required": ["query"],
            },
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    try:
        # Gehirn
        if name == "brain_list":
            from jarvis.tools import brain
            return brain.list_files()
        elif name == "brain_read":
            from jarvis.tools import brain
            return brain.read_file(**args)
        elif name == "brain_search":
            from jarvis.tools import brain
            return brain.search_files(**args)
        elif name == "brain_delete":
            from jarvis.tools import brain
            return brain.delete_file(**args)
        # Todo-Liste
        if name == "todo_add":
            from jarvis.tools import todo
            return todo.add_task(**args)
        elif name == "todo_list":
            from jarvis.tools import todo
            return todo.list_tasks(**args)
        elif name == "todo_complete":
            from jarvis.tools import todo
            return todo.complete_task(**args)
        elif name == "todo_delete":
            from jarvis.tools import todo
            return todo.delete_task(**args)
        elif name == "todo_update":
            from jarvis.tools import todo
            return todo.update_task(**args)
        # Morning Briefing
        elif name == "morning_briefing":
            from jarvis.tools import briefing
            return briefing.morning_briefing(**args)
        # Hardware Agent
        elif name == "hardware_load_datasheet":
            from jarvis.tools import hardware
            return hardware.load_datasheet(**args)
        elif name == "hardware_query_component":
            from jarvis.tools import hardware
            return hardware.query_component(**args)
        elif name == "hardware_list_components":
            from jarvis.tools import hardware
            return hardware.list_components()
        elif name == "hardware_schematic_hints":
            from jarvis.tools import hardware
            return hardware.schematic_hints(**args)
        # Claude Coding
        if name == "claude_generate_code":
            from jarvis.tools import claude_coder
            return claude_coder.generate_code(**args)
        elif name == "claude_review_code":
            from jarvis.tools import claude_coder
            return claude_coder.review_code(**args)
        elif name == "claude_explain_code":
            from jarvis.tools import claude_coder
            return claude_coder.explain_code(**args)
        # Web-Suche
        if name == "web_search":
            from jarvis.tools import web_search
            return web_search.search(**args)
        elif name == "web_fetch_page":
            from jarvis.tools import web_search
            return web_search.fetch_page(**args)
        # GitHub
        elif name == "github_list_repos":
            return github.list_repos()
        elif name == "github_read_file":
            return github.read_file(**args)
        elif name == "github_write_file":
            return github.write_file(**args)
        elif name == "github_list_files":
            return github.list_files(**args)
        # Notion
        elif name == "notion_search":
            return notion.search(**args)
        elif name == "notion_read_page":
            return notion.read_page(**args)
        elif name == "notion_create_page":
            return notion.create_page(**args)
        # Google Calendar
        elif name == "calendar_list_events":
            from jarvis.tools import google_calendar
            return google_calendar.list_events(**args)
        elif name == "calendar_create_event":
            from jarvis.tools import google_calendar
            return google_calendar.create_event(**args)
        elif name == "calendar_delete_event":
            from jarvis.tools import google_calendar
            return google_calendar.delete_event(**args)
        elif name == "calendar_list_calendars":
            from jarvis.tools import google_calendar
            return google_calendar.list_calendars()
        # Gmail
        elif name == "gmail_list_emails":
            from jarvis.tools import gmail
            return gmail.list_emails(**args)
        elif name == "gmail_read_email":
            from jarvis.tools import gmail
            return gmail.read_email(**args)
        elif name == "gmail_send_email":
            from jarvis.tools import gmail
            return gmail.send_email(**args)
        elif name == "gmail_search_emails":
            from jarvis.tools import gmail
            return gmail.search_emails(**args)
        else:
            return f"Unbekanntes Tool: {name}"
    except Exception as e:
        return f"Tool-Fehler ({name}): {str(e)}"
