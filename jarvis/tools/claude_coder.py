import anthropic
import config

_client = None

CODING_SYSTEM = """\
Du bist ein erstklassiger Software-Ingenieur. Deine Aufgabe ist es, sauberen, \
funktionierenden Code zu schreiben.

Regeln:
- Code immer in Englisch (Variablen, Kommentare, Docstrings)
- Antwort auf Deutsch, Code auf Englisch
- Schreibe vollständigen, lauffähigen Code — keine Platzhalter wie "# TODO"
- Kurze Erklärung VOR dem Code, was der Code tut
- Keine unnötigen Kommentare im Code selbst
- Nutze moderne Best Practices für die jeweilige Sprache
"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY nicht konfiguriert (.env)")
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def generate_code(task: str, language: str = "", context: str = "") -> str:
    """Lässt Claude Opus 4.7 Code für eine Aufgabe generieren."""
    client = _get_client()

    user_msg = f"Aufgabe: {task}"
    if language:
        user_msg += f"\nSprache/Framework: {language}"
    if context:
        user_msg += f"\nKontext/Anforderungen:\n{context}"

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=CODING_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        final = stream.get_final_message()

    parts = []
    for block in final.content:
        if block.type == "text":
            parts.append(block.text)

    return "\n".join(parts) if parts else "Kein Code generiert."


def review_code(code: str, language: str = "") -> str:
    """Lässt Claude Opus 4.7 Code reviewen und verbessern."""
    client = _get_client()

    user_msg = f"Reviewe und verbessere diesen Code:\n\n```{language}\n{code}\n```"

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=CODING_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        final = stream.get_final_message()

    parts = [block.text for block in final.content if block.type == "text"]
    return "\n".join(parts) if parts else "Kein Review generiert."


def explain_code(code: str, language: str = "") -> str:
    """Lässt Claude Opus 4.7 Code erklären."""
    client = _get_client()

    user_msg = f"Erkläre diesen Code detailliert auf Deutsch:\n\n```{language}\n{code}\n```"

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=CODING_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        final = stream.get_final_message()

    parts = [block.text for block in final.content if block.type == "text"]
    return "\n".join(parts) if parts else "Keine Erklärung generiert."
