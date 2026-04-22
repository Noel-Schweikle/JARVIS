import os
from dotenv import load_dotenv

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
GOOGLE_CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_PATH", os.path.join(_BASE_DIR, "credentials.json")
)
GOOGLE_TOKEN_PATH = os.getenv(
    "GOOGLE_TOKEN_PATH", os.path.join(_BASE_DIR, "token.json")
)
MODEL = "gpt-4o-mini"
TTS_VOICE = os.getenv("TTS_VOICE", "alloy")
