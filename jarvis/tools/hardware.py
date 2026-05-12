"""Hardware/Embedded Agent — Datasheet-Verwaltung und Bauteilabfragen."""
import json
import os
import re
import urllib.request
import urllib.parse
from typing import Optional

_STORAGE_DIR = os.path.expanduser("~/.jarvis/datasheets")
_INDEX_FILE = os.path.join(_STORAGE_DIR, "_index.json")

# Schlüsselwörter für automatische Spec-Extraktion
_SPEC_PATTERNS = {
    "flash":      [r"(\d+\s*[KkMm]?[Bb])\s*(?:bytes?\s+)?(?:of\s+)?(?:in-system\s+)?(?:self-programmable\s+)?flash",
                   r"flash\s*(?:memory|program\s+memory)[:\s]+(\d+\s*[KkMm][Bb])",
                   r"(\d+)\s*[Kk]\s*(?:words?|bytes?)\s+(?:flash|program)"],
    "ram":        [r"(\d+\s*[KkMm]?[Bb])\s*(?:bytes?\s+)?(?:internal\s+)?sram",
                   r"sram[:\s]+(\d+\s*[KkMm][Bb])",
                   r"(\d+)\s*[Kk]\s*bytes?\s+(?:internal\s+)?sram"],
    "eeprom":     [r"(\d+\s*[KkMm]?[Bb])\s*(?:bytes?\s+)?eeprom",
                   r"eeprom[:\s]+(\d+\s*[KkMm][Bb])"],
    "clock_mhz":  [r"(\d+)\s*mhz\s+(?:max(?:imum)?\s+)?(?:operating\s+)?(?:frequency|clock)",
                   r"up\s+to\s+(\d+)\s*mhz",
                   r"(\d+)\s*mhz\s+(?:cpu|core)"],
    "gpio":       [r"(\d+)\s+(?:programmable\s+)?(?:i/o\s+(?:lines|pins)|gpio)",
                   r"gpio[:\s]+(\d+)",
                   r"(\d+)\s+i/o\s+(?:pins?|lines?)"],
    "adc_bits":   [r"(\d+)[\s-]*bit\s+adc",
                   r"adc[:\s]+(\d+)[\s-]*bit"],
    "adc_channels": [r"(\d+)[\s-]*channel\s+(?:10|12)[\s-]*bit\s*adc",
                     r"(\d+)\s+adc\s+channels?"],
    "uart":       [r"(\d+)\s+(?:programmable\s+)?usart",
                   r"usart[:/\s]+(\d+)",
                   r"(\d+)\s+uart"],
    "spi":        [r"(\d+)\s+spi\b",
                   r"spi[:/\s]+(\d+)"],
    "i2c":        [r"(\d+)\s+(?:two[\s-]wire|i2c|twi)\b",
                   r"(?:two[\s-]wire|i2c|twi)[:/\s]+(\d+)"],
    "voltage_min": [r"(\d+(?:\.\d+)?)\s*v\s*(?:to|-)\s*\d",
                    r"vcc[:\s]+(\d+(?:\.\d+)?)\s*v"],
    "voltage_max": [r"\d+(?:\.\d+)?\s*v\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*v",
                    r"vcc[^,]+,\s*(\d+(?:\.\d+)?)\s*v\s*max"],
    "package":    [r"available\s+in\s+([\w\s,/]+(?:package|dip|qfp|qfn|tqfp|soic|pdip)[\w\s]*)",
                   r"((?:pdip|tqfp|qfn|soic|mlf|dip|qfp)[\w\s\-/]*)(?:\s+package)?"],
    "timers":     [r"(\d+)\s+(?:8[\s-]*bit|16[\s-]*bit)?\s*(?:timer|counter)",
                   r"timer[s/]+counter[s]?[:\s]+(\d+)"],
    "pwm":        [r"(\d+)\s+pwm\s+(?:channels?|outputs?)",
                   r"pwm[:\s]+(\d+)"],
}

_SCHEMATIC_HINTS = {
    "avr": """
**Mindest-Schaltplan Hinweise (AVR)**

1. **Versorgung (VCC/AVCC)**
   - 100 nF Keramik-Kondensator von VCC nach GND (direkt am IC-Pin)
   - 10 µF Elko von VCC nach GND (pro Versorgungsdomäne)
   - AVCC separat entkoppeln: 100 nF + 10 µH Drossel nach VCC

2. **Reset-Schaltung**
   - 10 kΩ Pull-up von RESET nach VCC
   - 100 nF von RESET nach GND (Entstörung)
   - Optional: Taster zwischen RESET und GND

3. **Quarz/Taktquelle**
   - Last-Kondensatoren: typisch 12–22 pF von XTAL1 und XTAL2 nach GND
   - Quarz-Gehäuse erden (EMV)
   - Leiterbahnen so kurz wie möglich

4. **ISP/JTAG Header (6-pin ISP)**
   - MISO, MOSI, SCK, RESET, VCC, GND
   - 10 Ω Serien-Widerstand auf MISO/MOSI/SCK empfohlen

5. **Allgemein**
   - Abblockkondensatoren direkt am IC (< 5 mm)
   - Sternförmige GND-Führung
   - Digitale und analoge GND trennen, nur an einem Punkt verbinden
""",
    "stm32": """
**Mindest-Schaltplan Hinweise (STM32)**

1. **Versorgung**
   - 100 nF + 1 µF Keramik je VDD/VDDA-Pin
   - VBAT: 100 nF + 1 µF wenn RTC/Backup genutzt

2. **BOOT0**
   - 10 kΩ Pull-down nach GND (normaler Betrieb: Flash-Boot)
   - Optional Taster zu VDD für DFU-Modus

3. **NRST**
   - 100 nF nach GND
   - Kein externer Pull-up nötig (intern)

4. **SWD-Debug-Header (4-pin)**
   - SWDIO, SWDCLK, VCC, GND
   - 10 kΩ Pull-up auf SWDIO
""",
}


def _load_index() -> dict:
    if not os.path.exists(_INDEX_FILE):
        return {}
    with open(_INDEX_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_index(index: dict) -> None:
    os.makedirs(_STORAGE_DIR, exist_ok=True)
    with open(_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _extract_specs(text: str) -> dict:
    text_lower = text.lower()
    specs: dict = {}
    for key, patterns in _SPEC_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, text_lower)
            if m:
                specs[key] = m.group(1).strip().upper()
                break
    return specs


def _extract_text_from_pdf(path: str) -> str:
    try:
        import pdfplumber
        lines = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:30]:  # max 30 Seiten
                t = page.extract_text()
                if t:
                    lines.append(t)
        return "\n".join(lines)
    except ImportError:
        return _extract_text_from_pdf_fallback(path)
    except Exception as e:
        return f"PDF-Fehler: {e}"


def _extract_text_from_pdf_fallback(path: str) -> str:
    """Fallback: rohe Bytes nach druckbaren ASCII-Strings durchsuchen."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
        strings = re.findall(rb"[\x20-\x7E]{4,}", raw)
        return " ".join(s.decode("ascii", errors="replace") for s in strings[:5000])
    except Exception as e:
        return f"Fallback-Fehler: {e}"


def _fetch_pdf_from_url(url: str) -> Optional[str]:
    """Lädt ein PDF von einer URL in eine temporäre Datei."""
    try:
        import tempfile
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 JARVIS/1.0"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        suffix = ".pdf" if url.lower().endswith(".pdf") else ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            return tmp.name
    except Exception as e:
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def load_datasheet(source: str, component_name: Optional[str] = None) -> str:
    """
    Lädt ein Datasheet (lokale PDF-Datei oder URL) und extrahiert Kennwerte.
    source: Dateipfad oder URL zum PDF
    component_name: Name des Bauteils (z.B. 'ATmega1284P'), Standard = Dateiname
    """
    tmp_path = None
    if source.startswith("http://") or source.startswith("https://"):
        tmp_path = _fetch_pdf_from_url(source)
        if not tmp_path:
            return f"Fehler: Konnte PDF nicht von {source} laden."
        pdf_path = tmp_path
        if not component_name:
            component_name = urllib.parse.urlparse(source).path.split("/")[-1].replace(".pdf", "")
    else:
        pdf_path = os.path.expanduser(source)
        if not os.path.exists(pdf_path):
            return f"Datei nicht gefunden: {pdf_path}"
        if not component_name:
            component_name = os.path.basename(pdf_path).replace(".pdf", "").replace("_", " ")

    component_name = component_name.upper().strip()
    text = _extract_text_from_pdf(pdf_path)

    if tmp_path:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    if text.startswith("PDF-Fehler") or text.startswith("Fallback-Fehler"):
        return f"Konnte Datasheet nicht lesen: {text}"

    specs = _extract_specs(text)
    # Erste 2000 Zeichen als Kurztext speichern
    summary = text[:2000].strip()

    index = _load_index()
    index[component_name] = {
        "specs": specs,
        "summary": summary,
        "source": source,
    }
    _save_index(index)

    lines = [f"📦 **{component_name}** — Datasheet geladen\n", "**Extrahierte Kennwerte:**"]
    _labels = {
        "flash": "Flash", "ram": "SRAM", "eeprom": "EEPROM",
        "clock_mhz": "Max. Takt", "gpio": "GPIO-Pins",
        "adc_bits": "ADC Auflösung", "adc_channels": "ADC Kanäle",
        "uart": "USART/UART", "spi": "SPI", "i2c": "I2C/TWI",
        "voltage_min": "VCC min", "voltage_max": "VCC max",
        "package": "Gehäuse", "timers": "Timer/Counter", "pwm": "PWM Kanäle",
    }
    for key, label in _labels.items():
        if key in specs:
            lines.append(f"  • {label}: {specs[key]}")

    if not specs:
        lines.append("  (Keine Kennwerte automatisch erkannt — Abfragen trotzdem möglich)")

    return "\n".join(lines)


def query_component(component_name: str, question: str) -> str:
    """
    Beantwortet eine Frage zu einem geladenen Bauteil.
    Beispiel: component_name='ATMEGA1284P', question='Wie viel RAM?'
    """
    index = _load_index()
    name_upper = component_name.upper().strip()

    # Fuzzy-Suche
    match = None
    for key in index:
        if name_upper in key or key in name_upper:
            match = key
            break
    if match is None:
        available = ", ".join(index.keys()) if index else "keine"
        return f"Bauteil '{component_name}' nicht gefunden. Verfügbar: {available}"

    entry = index[match]
    specs = entry.get("specs", {})
    summary = entry.get("summary", "")
    q_lower = question.lower()

    _labels = {
        "flash": ["flash", "programmspeicher", "program memory"],
        "ram": ["ram", "sram", "arbeitsspeicher", "work memory"],
        "eeprom": ["eeprom"],
        "clock_mhz": ["takt", "frequenz", "clock", "mhz", "speed"],
        "gpio": ["gpio", "i/o", "io pins", "pins", "port"],
        "adc_bits": ["adc", "analog", "auflösung", "bit"],
        "adc_channels": ["adc kanal", "adc channel", "analog channel", "analog input"],
        "uart": ["uart", "usart", "seriell", "serial"],
        "spi": ["spi"],
        "i2c": ["i2c", "twi", "two wire"],
        "voltage_min": ["spannung", "voltage", "vcc", "versorgung"],
        "voltage_max": ["spannung", "voltage", "vcc", "versorgung"],
        "package": ["gehäuse", "package", "bauform"],
        "timers": ["timer", "counter", "zähler"],
        "pwm": ["pwm"],
    }

    answers = []
    for spec_key, keywords in _labels.items():
        if any(kw in q_lower for kw in keywords) and spec_key in specs:
            answers.append(f"**{spec_key.upper()}:** {specs[spec_key]}")

    if answers:
        return f"**{match}** — {question}\n" + "\n".join(answers)

    # Fallback: alle Specs anzeigen
    if specs:
        lines = [f"**{match}** — Alle bekannten Kennwerte:"]
        for k, v in specs.items():
            lines.append(f"  • {k}: {v}")
        return "\n".join(lines)

    # Letzter Fallback: Rohauszug
    if summary:
        return f"Keine strukturierten Daten für '{question}' gefunden. Rohdaten-Auszug:\n{summary[:800]}"
    return f"Keine Daten für '{component_name}' vorhanden."


def list_components() -> str:
    """Listet alle geladenen Bauteile mit ihren Kennwerten auf."""
    index = _load_index()
    if not index:
        return "Keine Datasheets geladen. Nutze `hardware_load_datasheet` um Datasheets hinzuzufügen."

    lines = [f"**Geladene Datasheets ({len(index)} Bauteil(e))**\n"]
    for name, entry in index.items():
        specs = entry.get("specs", {})
        spec_summary = ", ".join(f"{k}={v}" for k, v in list(specs.items())[:5])
        lines.append(f"• **{name}** — {spec_summary or 'keine Kennwerte extrahiert'}")
    return "\n".join(lines)


def schematic_hints(component_name: str) -> str:
    """
    Gibt Mindest-Schaltplan-Hinweise für ein Bauteil zurück
    (Entkopplung, Reset, Takt, Debug-Header etc.).
    """
    name_lower = component_name.lower()

    if any(x in name_lower for x in ["atmega", "attiny", "avr", "atmel"]):
        return f"**Schaltplan-Hinweise für {component_name.upper()} (AVR)**" + _SCHEMATIC_HINTS["avr"]
    if any(x in name_lower for x in ["stm32", "stm"]):
        return f"**Schaltplan-Hinweise für {component_name.upper()} (STM32)**" + _SCHEMATIC_HINTS["stm32"]

    # Allgemeine Tipps
    return f"""**Allgemeine Schaltplan-Hinweise für {component_name.upper()}**

1. **Abblockkondensatoren** — 100 nF Keramik direkt an jeden VCC-Pin
2. **Bulk-Kapazität** — 10 µF Elko pro Versorgungsdomäne
3. **Reset** — Pull-up (10 kΩ) + 100 nF Entstörkondensator nach GND
4. **Quarz** — Last-Kondensatoren (12–22 pF) nach GND, kurze Leiterbahnen
5. **GND-Plane** — Durchgängige GND-Fläche, Sterntopologie vermeiden
6. **Debug-Interface** — SWD/JTAG/ISP Header mit Serien-Widerständen

Lade das Datasheet via `hardware_load_datasheet` für bauteilspezifische Hinweise.
"""
