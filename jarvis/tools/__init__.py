import json
from jarvis.tools import github, notion

TOOL_SCHEMAS = [
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
        # GitHub
        if name == "github_list_repos":
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
