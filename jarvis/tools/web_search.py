import json
import re
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser


# ── Minimal HTML → Text ───────────────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "head", "nav", "footer", "noscript"}

    def __init__(self):
        super().__init__()
        self._skip = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip == 0:
            text = data.strip()
            if text:
                self.chunks.append(text)


def _html_to_text(html: str, max_chars: int = 8000) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = "\n".join(parser.chunks)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:max_chars]


# ── DuckDuckGo Search (HTML scraping, kein API-Key) ───────────────────────────

def search(query: str, max_results: int = 5) -> str:
    """Sucht im Web via DuckDuckGo HTML-Interface (keine API-Key nötig)."""
    try:
        encoded = urllib.parse.urlencode({"q": query, "kl": "de-de"})
        url = "https://html.duckduckgo.com/html/"
        data = encoded.encode("utf-8")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            ),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Ergebnisse extrahieren
        results = []
        # Treffer-Blöcke finden
        blocks = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        for href, title_html, snippet_html in blocks[:max_results]:
            title = urllib.parse.unquote_plus(re.sub(r"<[^>]+>", "", title_html).strip())
            snippet = urllib.parse.unquote_plus(re.sub(r"<[^>]+>", "", snippet_html).strip())
            from html import unescape
            title = unescape(title)
            snippet = unescape(snippet)
            # Werbeanzeigen überspringen
            if "duckduckgo.com/y.js" in href:
                continue
            # DuckDuckGo redirect-URLs entschlüsseln
            if href.startswith("//duckduckgo.com/l/"):
                parsed = urllib.parse.urlparse("https:" + href)
                qs = urllib.parse.parse_qs(parsed.query)
                href = qs.get("uddg", [href])[0]
            results.append({"title": title, "url": href, "snippet": snippet})

        if not results:
            return f"Keine Ergebnisse für: {query}"

        lines = [f"**Suchergebnisse für: {query}**\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. [{r['title']}]({r['url']})")
            lines.append(f"   {r['snippet']}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Web-Suche fehlgeschlagen: {e}"


# ── Webpage Fetch ─────────────────────────────────────────────────────────────

def fetch_page(url: str, max_chars: int = 6000) -> str:
    """Lädt eine Webseite und gibt den Textinhalt zurück."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "")
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()
            html = resp.read().decode(charset, errors="replace")
        text = _html_to_text(html, max_chars)
        return f"**Inhalt von {url}:**\n\n{text}"
    except urllib.error.HTTPError as e:
        return f"HTTP-Fehler {e.code} beim Abrufen von {url}"
    except urllib.error.URLError as e:
        return f"URL-Fehler beim Abrufen von {url}: {e.reason}"
    except Exception as e:
        return f"Fehler beim Abrufen von {url}: {e}"
