import json
from jarvis.tools import github, notion

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "github_read_file",
            "description": "Liest eine Datei aus dem GitHub Repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Dateipfad im Repository",
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository owner/name (optional, nutzt Standard-Repo)",
                    },
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
                    "path": {"type": "string", "description": "Dateipfad im Repository"},
                    "content": {"type": "string", "description": "Dateiinhalt"},
                    "message": {"type": "string", "description": "Commit-Nachricht"},
                    "repo": {
                        "type": "string",
                        "description": "Repository owner/name (optional)",
                    },
                },
                "required": ["path", "content", "message"],
            },
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
                    "path": {
                        "type": "string",
                        "description": "Verzeichnispfad (leer für Root)",
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository owner/name (optional)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notion_search",
            "description": "Sucht in Notion nach Seiten und Datenbank-Einträgen",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Suchbegriff"}
                },
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
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "Notion Page ID (aus notion_search)",
                    }
                },
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
                    "title": {"type": "string", "description": "Seitentitel"},
                    "content": {
                        "type": "string",
                        "description": "Seiteninhalt (Markdown-Format)",
                    },
                },
                "required": ["title", "content"],
            },
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "github_read_file":
            return github.read_file(**args)
        elif name == "github_write_file":
            return github.write_file(**args)
        elif name == "github_list_files":
            return github.list_files(**args)
        elif name == "notion_search":
            return notion.search(**args)
        elif name == "notion_read_page":
            return notion.read_page(**args)
        elif name == "notion_create_page":
            return notion.create_page(**args)
        else:
            return f"Unbekanntes Tool: {name}"
    except Exception as e:
        return f"Tool-Fehler ({name}): {str(e)}"
