"""
Einmaliges Skript zum Einrichten der Google OAuth2-Authentifizierung.
Ausführen mit: python3 setup_google.py
"""
from jarvis.tools.google_auth import get_credentials

print("Starte Google OAuth2-Authentifizierung...")
creds = get_credentials()
print(f"Erfolg! Token gespeichert. Gültig bis: {creds.expiry}")
print("JARVIS kann jetzt auf Google Calendar und Gmail zugreifen.")
