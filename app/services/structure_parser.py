import re
from typing import Dict


def _looks_like_noise(text: str) -> bool:
    text = text.strip()
    if not text:
        return True
    if len(text) <= 2:
        return True
    if re.match(r"^\d+$", text):
        return True
    if re.match(r"^page\s+\d+", text.lower()):
        return True
    return False


def parse_structure(document: Dict) -> Dict:
    cleaned_articles = []

    for article in document.get("articles", []):
        sections = []

        for sec in article.get("sections", []):
            merged = []
            buffer = ""

            for item in sec.get("content", []):
                if item["type"] == "text":
                    txt = item["value"].strip()
                    if _looks_like_noise(txt):
                        continue
                    buffer = f"{buffer} {txt}".strip()
                else:
                    if buffer:
                        merged.append({"type": "text", "value": buffer})
                        buffer = ""
                    merged.append(item)

            if buffer:
                merged.append({"type": "text", "value": buffer})

            if merged:
                sections.append({
                    "section_id": sec["section_id"],
                    "title": sec["title"],
                    "content": merged
                })

        if sections:
            cleaned_articles.append({
                "article_title": article["article_title"],
                "sections": sections
            })

    document["articles"] = cleaned_articles
    return document
