# app/services/pdf_extractor.py

import pdfplumber
import statistics
import re
import os


# -----------------------------
# Helpers
# -----------------------------

def _is_heading(text: str) -> bool:
    """
    Heuristic to detect subheadings.
    """
    text = text.strip()
    if not text:
        return False

    # numbered headings: 1., 1.1, 2.3.4
    if re.match(r"^\d+(\.\d+)*\s+", text):
        return True

    # short ALL CAPS headings (subheading only)
    if text.isupper() and len(text.split()) <= 8:
        return True

    return False


def _is_article_heading(text: str) -> bool:
    """
    Strict rule to detect ARTICLES only.
    """
    text = text.strip()

    # ARTICLE I, ARTICLE II, ARTICLE 1, ARTICLE 1.
    if re.match(r"^ARTICLE\s+([IVX]+|\d+)(\b|[\.\:])", text, re.IGNORECASE):
        return True

    return False


def _is_exhibit_heading(text: str) -> bool:
    """
    Detect EXHIBIT sections (must NOT become articles)
    """
    return bool(re.match(r"^EXHIBIT\s+[A-Z]", text.strip(), re.IGNORECASE))


def _is_schedule_heading(text: str) -> bool:
    """
    Detect SCHEDULE sections (must NOT become articles)
    """
    return bool(re.match(r"^SCHEDULE\s+\d+", text.strip(), re.IGNORECASE))


def _table_to_text(table):
    lines = []
    for row in table:
        clean_row = [cell.strip() if cell else "" for cell in row]
        lines.append(" | ".join(clean_row))
    return "\n".join(lines)


# -----------------------------
# Main extractor
# -----------------------------

def extract_pdf(file_path: str) -> dict:

    default_title = os.path.splitext(os.path.basename(file_path))[0]

    document = {
        "document_title": None,
        "articles": []
    }

    current_article = None
    current_subheading = None

    with pdfplumber.open(file_path) as pdf:

        # Font analysis
        font_sizes = []
        for page in pdf.pages[:5]:
            for word in page.extract_words(extra_attrs=["size"]):
                font_sizes.append(word["size"])

        avg_font = statistics.mean(font_sizes) if font_sizes else 10

        for page_number, page in enumerate(pdf.pages, start=1):

            tables = page.extract_tables()
            table_texts = [_table_to_text(t) for t in tables]

            words = page.extract_words(
                use_text_flow=True,
                extra_attrs=["size"]
            )

            lines = {}
            for w in words:
                y = round(w["top"], 1)
                lines.setdefault(y, []).append(w)

            for y in sorted(lines.keys()):
                line_words = lines[y]
                text = " ".join(w["text"] for w in line_words).strip()
                avg_size = statistics.mean(w["size"] for w in line_words)

                # -------------------------
                # DOCUMENT TITLE
                # -------------------------
                if avg_size > avg_font * 1.6:
                    if not document["document_title"]:
                        document["document_title"] = text
                        continue

                # -------------------------
                # ARTICLE DETECTION
                # -------------------------
                if _is_article_heading(text):
                    current_article = {
                        "article_title": text,
                        "subheadings": []
                    }
                    document["articles"].append(current_article)
                    current_subheading = None
                    continue

                # -------------------------
                # EXHIBITS / SCHEDULES (STOP INHERITANCE)
                # -------------------------
                if _is_exhibit_heading(text) or _is_schedule_heading(text):
                    current_article = None
                    current_subheading = None
                    continue

                # -------------------------
                # SUBHEADING
                # -------------------------
                if current_article and (avg_size > avg_font * 1.2 or _is_heading(text)):
                    current_subheading = {
                        "title": text,
                        "content": []
                    }
                    current_article["subheadings"].append(current_subheading)
                    continue

                # -------------------------
                # BODY TEXT
                # -------------------------
                if current_subheading:
                    current_subheading["content"].append({
                        "type": "text",
                        "value": text,
                        "page": page_number
                    })

            # -------------------------
            # ATTACH TABLES
            # -------------------------
            if current_subheading:
                for t in table_texts:
                    current_subheading["content"].append({
                        "type": "table",
                        "value": t,
                        "page": page_number
                    })

    if not document["document_title"]:
        document["document_title"] = default_title

    return document
