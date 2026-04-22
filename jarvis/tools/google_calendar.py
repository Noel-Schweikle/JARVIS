from datetime import datetime, timezone
from googleapiclient.discovery import build
from jarvis.tools.google_auth import get_credentials


def _service():
    return build("calendar", "v3", credentials=get_credentials())


def list_events(max_results: int = 10, calendar_id: str = "primary") -> str:
    svc = _service()
    now = datetime.now(timezone.utc).isoformat()
    result = (
        svc.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = result.get("items", [])
    if not events:
        return "Keine bevorstehenden Termine gefunden."

    lines = []
    for e in events:
        start = e["start"].get("dateTime", e["start"].get("date", ""))
        lines.append(f"[{start}] {e.get('summary', '(kein Titel)')} — ID: {e['id']}")
    return "\n".join(lines)


def create_event(
    summary: str,
    start: str,
    end: str,
    description: str = "",
    location: str = "",
    calendar_id: str = "primary",
) -> str:
    """start/end als ISO-8601 String, z.B. '2024-06-01T14:00:00+02:00'."""
    svc = _service()
    body = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {"dateTime": start, "timeZone": "Europe/Berlin"},
        "end": {"dateTime": end, "timeZone": "Europe/Berlin"},
    }
    event = svc.events().insert(calendarId=calendar_id, body=body).execute()
    return f"Termin erstellt: {event.get('summary')} — {event.get('htmlLink')}"


def delete_event(event_id: str, calendar_id: str = "primary") -> str:
    svc = _service()
    svc.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    return f"Termin {event_id} gelöscht."


def list_calendars() -> str:
    svc = _service()
    result = svc.calendarList().list().execute()
    items = result.get("items", [])
    if not items:
        return "Keine Kalender gefunden."
    return "\n".join(f"{c['id']}  —  {c.get('summary', '')}" for c in items)
