# app/services/structure_parser.py

import re
from typing import Dict, List


# -----------------------------
# Helper rules
# -----------------------------

def _looks_like_noise(text: str) -> bool:
    text = text.strip()

    if not text:
        return True

    if len(text) <= 2:
        return True

    if re.match(r"^page\s+\d+", text.lower()):
        return True

    if re.match(r"^\d+$", text):
        return True

    return False


def _is_probably_heading(title: str) -> bool:
    words = title.split()

    if len(words) > 15:
        return False

    if title.endswith("."):
        return False

    return True


def _normalize_article_title(title: str) -> str:
    """
    Normalize ARTICLE titles strictly.
    """
    title = title.strip()

    # Extract only "ARTICLE <number>"
    match = re.match(
        r"(ARTICLE\s+([IVX]+|\d+))",
        title,
        re.IGNORECASE
    )

    if match:
        return match.group(1).upper()

    return "General"


# -----------------------------
# Core parser
# -----------------------------

def parse_structure(document: Dict) -> Dict:

    cleaned_articles = []

    # ---------
    # FIX DOCUMENT TITLE
    # ---------
    if document.get("document_title", "").upper() == "EXECUTION VERSION":
        document["document_title"] = "Credit Agreement"

    for article in document.get("articles", []):

        raw_article_title = article.get("article_title", "")
        article_title = _normalize_article_title(raw_article_title)

        cleaned_subheadings = []

        for sub in article.get("subheadings", []):
            title = sub.get("title", "").strip()

            if not _is_probably_heading(title):
                if cleaned_subheadings:
                    cleaned_subheadings[-1]["content"].extend(sub["content"])
                continue

            merged_content = []
            buffer = ""

            for item in sub.get("content", []):
                if item["type"] == "text":
                    text = item["value"].strip()

                    if _looks_like_noise(text):
                        continue

                    if buffer:
                        buffer += " " + text
                    else:
                        buffer = text
                else:
                    if buffer:
                        merged_content.append({
                            "type": "text",
                            "value": buffer
                        })
                        buffer = ""

                    merged_content.append(item)

            if buffer:
                merged_content.append({
                    "type": "text",
                    "value": buffer
                })

            if not merged_content:
                continue

            cleaned_subheadings.append({
                "title": title,
                "content": merged_content
            })

        if cleaned_subheadings:
            cleaned_articles.append({
                "article_title": article_title,
                "subheadings": cleaned_subheadings
            })

    document["articles"] = cleaned_articles
    return document
