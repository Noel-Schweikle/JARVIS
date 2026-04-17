from notion_client import Client
import config

_notion = None


def _get_notion() -> Client:
    global _notion
    if _notion is None:
        _notion = Client(auth=config.NOTION_TOKEN)
    return _notion


def search(query: str) -> str:
    if not config.NOTION_TOKEN:
        return "Fehler: Kein Notion Token konfiguriert (NOTION_TOKEN in .env setzen)"

    notion = _get_notion()
    try:
        results = notion.search(query=query, page_size=8)
        if not results["results"]:
            return "Keine Ergebnisse gefunden."

        lines = []
        for item in results["results"]:
            obj_type = item["object"]
            title = _extract_title(item)
            lines.append(f"[{obj_type}] {title}  (ID: {item['id']})")
        return "\n".join(lines)
    except Exception as e:
        return f"Notion Fehler: {str(e)}"


def read_page(page_id: str) -> str:
    if not config.NOTION_TOKEN:
        return "Fehler: Kein Notion Token konfiguriert"

    notion = _get_notion()
    try:
        page = notion.pages.retrieve(page_id)
        blocks = notion.blocks.children.list(page_id)

        title = _extract_title(page)
        lines = [f"# {title}\n"]
        for block in blocks["results"]:
            text = _block_to_text(block)
            if text:
                lines.append(text)
        return "\n".join(lines)
    except Exception as e:
        return f"Notion Fehler: {str(e)}"


def create_page(title: str, content: str) -> str:
    if not config.NOTION_TOKEN:
        return "Fehler: Kein Notion Token konfiguriert"
    if not config.NOTION_DATABASE_ID:
        return "Fehler: Keine Notion Database ID konfiguriert (NOTION_DATABASE_ID in .env setzen)"

    notion = _get_notion()
    try:
        blocks = _markdown_to_blocks(content)
        page = notion.pages.create(
            parent={"database_id": config.NOTION_DATABASE_ID},
            properties={
                "title": {"title": [{"text": {"content": title}}]}
            },
            children=blocks,
        )
        return f"Notion-Seite erstellt: {title}  (ID: {page['id']})"
    except Exception as e:
        return f"Notion Fehler: {str(e)}"


def _extract_title(item: dict) -> str:
    try:
        props = item.get("properties", {})
        for key in ("Name", "Title", "title"):
            if key in props:
                rich = props[key].get("title", [])
                if rich:
                    return rich[0]["plain_text"]
        raw = item.get("title", [])
        if raw:
            return raw[0]["plain_text"]
    except Exception:
        pass
    return item.get("id", "Unbekannt")


def _block_to_text(block: dict) -> str:
    btype = block.get("type", "")
    try:
        rich = block.get(btype, {}).get("rich_text", [])
        text = "".join(r.get("plain_text", "") for r in rich)
        prefix = {
            "heading_1": "# ",
            "heading_2": "## ",
            "heading_3": "### ",
            "bulleted_list_item": "- ",
            "numbered_list_item": "1. ",
        }.get(btype, "")
        if btype == "code":
            lang = block.get(btype, {}).get("language", "")
            return f"```{lang}\n{text}\n```"
        return prefix + text if text else ""
    except Exception:
        return ""


def _markdown_to_blocks(content: str) -> list:
    blocks = []
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            btype, text = "heading_1", line[2:]
        elif line.startswith("## "):
            btype, text = "heading_2", line[3:]
        elif line.startswith("### "):
            btype, text = "heading_3", line[4:]
        elif line.startswith("- "):
            btype, text = "bulleted_list_item", line[2:]
        else:
            btype, text = "paragraph", line

        blocks.append({
            "object": "block",
            "type": btype,
            btype: {"rich_text": [{"type": "text", "text": {"content": text}}]},
        })
    return blocks
