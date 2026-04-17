import io
import os
import tempfile
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
from openai import OpenAI
import config

_client = None

SAMPLE_RATE = 16000
CHANNELS = 1


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def record_audio(duration: int = 5) -> bytes:
    print(f"\n[Aufnahme läuft... {duration}s — bitte sprechen]")
    recording = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=np.int16,
    )
    sd.wait()
    print("[Aufnahme beendet]")

    buf = io.BytesIO()
    wav.write(buf, SAMPLE_RATE, recording)
    return buf.getvalue()


def transcribe(audio_bytes: bytes) -> str:
    client = _get_client()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="de",
            )
        return result.text
    finally:
        os.unlink(tmp_path)


def speak(text: str) -> None:
    client = _get_client()
    # Strip markdown for cleaner speech
    clean = _strip_markdown(text)
    response = client.audio.speech.create(
        model="tts-1",
        voice=config.TTS_VOICE,
        input=clean,
        response_format="wav",
    )
    buf = io.BytesIO(response.content)
    rate, data = wav.read(buf)
    sd.play(data, rate)
    sd.wait()


def listen(duration: int = 5) -> str:
    audio = record_audio(duration)
    return transcribe(audio)


def _strip_markdown(text: str) -> str:
    import re
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"[#*_~>]", "", text)
    text = re.sub(r"\n+", " ", text)
    return text.strip()
