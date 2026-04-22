import base64
import email as email_lib
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from jarvis.tools.google_auth import get_credentials


def _service():
    return build("gmail", "v1", credentials=get_credentials())


def list_emails(max_results: int = 10, query: str = "") -> str:
    svc = _service()
    params = {"userId": "me", "maxResults": max_results}
    if query:
        params["q"] = query
    result = svc.users().messages().list(**params).execute()
    messages = result.get("messages", [])
    if not messages:
        return "Keine E-Mails gefunden."

    lines = []
    for m in messages:
        meta = (
            svc.users()
            .messages()
            .get(userId="me", id=m["id"], format="metadata",
                 metadataHeaders=["Subject", "From", "Date"])
            .execute()
        )
        headers = {h["name"]: h["value"] for h in meta.get("payload", {}).get("headers", [])}
        lines.append(
            f"[{headers.get('Date', '')}] {headers.get('From', '')} — "
            f"{headers.get('Subject', '(kein Betreff)')} — ID: {m['id']}"
        )
    return "\n".join(lines)


def read_email(message_id: str) -> str:
    svc = _service()
    msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

    body = _extract_body(msg.get("payload", {}))

    return (
        f"Von: {headers.get('From', '')}\n"
        f"An: {headers.get('To', '')}\n"
        f"Datum: {headers.get('Date', '')}\n"
        f"Betreff: {headers.get('Subject', '')}\n"
        f"\n{body}"
    )


def send_email(to: str, subject: str, body: str) -> str:
    svc = _service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    return f"E-Mail gesendet. ID: {sent['id']}"


def search_emails(query: str, max_results: int = 10) -> str:
    return list_emails(max_results=max_results, query=query)


def _extract_body(payload: dict) -> str:
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        for part in payload["parts"]:
            result = _extract_body(part)
            if result:
                return result
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return "(Kein lesbarer Inhalt)"
