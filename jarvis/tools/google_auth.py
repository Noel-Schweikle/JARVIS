import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import config

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_credentials() -> Credentials:
    creds = None
    token_path = config.GOOGLE_TOKEN_PATH

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(config.GOOGLE_CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Google credentials.json nicht gefunden: {config.GOOGLE_CREDENTIALS_PATH}\n"
                    "Lade die Datei von https://console.cloud.google.com/ herunter und"
                    " lege sie am konfigurierten Pfad ab."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                config.GOOGLE_CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds
