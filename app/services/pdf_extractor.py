import pdfplumber
import statistics
import re
import os

# -----------------------------
# Regex
# -----------------------------
ARTICLE_REGEX = re.compile(
    r"^ARTICLE\s+([IVX]+|\d+)\b",
    re.IGNORECASE
)

SECTION_REGEX = re.compile(
    r"^(SECTION\s+)?(?P<num>\d+(\.\d+)+)\s*(?P<title>.+)?$",
    re.IGNORECASE
)

TOC_TITLES = {"TABLE OF CONTENTS", "CONTENTS"}


# -----------------------------
# Helpers
# -----------------------------
def _is_toc_heading(text: str) -> bool:
    return text.strip().upper() in TOC_TITLES


def _is_article_heading(text: str) -> bool:
    return bool(ARTICLE_REGEX.match(text.strip()))


def _is_exhibit_heading(text: str) -> bool:
    return bool(re.match(r"^EXHIBIT\s+[A-Z]", text.strip(), re.IGNORECASE))


def _is_schedule_heading(text: str) -> bool:
    return bool(re.match(r"^SCHEDULE\s+\d+", text.strip(), re.IGNORECASE))


def _is_section_heading(text: str):
    match = SECTION_REGEX.match(text.strip())
    if not match:
        return None
    return {
        "section_id": match.group("num"),
        "title": (match.group("title") or "").strip()
    }


def _table_to_text(table):
    rows = []
    for row in table:
        rows.append(" | ".join(cell.strip() if cell else "" for cell in row))
    return "\n".join(rows)


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
    current_section = None
    inside_toc = False

    with pdfplumber.open(file_path) as pdf:

        # --- font baseline ---
        font_sizes = []
        for page in pdf.pages[:5]:
            for w in page.extract_words(extra_attrs=["size"]):
                font_sizes.append(w["size"])
        avg_font = statistics.mean(font_sizes) if font_sizes else 10

        for page_no, page in enumerate(pdf.pages, start=1):

            tables = [_table_to_text(t) for t in page.extract_tables()]

            words = page.extract_words(
                use_text_flow=True,
                extra_attrs=["size"]
            )

            lines = {}
            for w in words:
                y = round(w["top"], 1)
                lines.setdefault(y, []).append(w)

            for y in sorted(lines):
                line_words = lines[y]
                text = " ".join(w["text"] for w in line_words).strip()
                avg_size = statistics.mean(w["size"] for w in line_words)

                if not text:
                    continue

                # -------------------------
                # Document title
                # -------------------------
                if avg_size > avg_font * 1.6 and not document["document_title"]:
                    document["document_title"] = text
                    continue

                # -------------------------
                # TOC handling
                # -------------------------
                if _is_toc_heading(text):
                    inside_toc = True
                    continue

                if inside_toc:
                    if _is_article_heading(text):
                        continue
                    if page_no > 3:
                        inside_toc = False
                    else:
                        continue

                # -------------------------
                # Stop at exhibits / schedules
                # -------------------------
                if _is_exhibit_heading(text) or _is_schedule_heading(text):
                    current_article = None
                    current_section = None
                    continue

                # -------------------------
                # Article
                # -------------------------
                if _is_article_heading(text):
                    article_id = ARTICLE_REGEX.match(text).group(0).upper()

                    current_article = {
                        "article_title": article_id,
                        "sections": []
                    }
                    document["articles"].append(current_article)
                    current_section = None
                    continue

                # -------------------------
                # Section
                # -------------------------
                section = _is_section_heading(text)
                if current_article and section:
                    current_section = {
                        "section_id": section["section_id"],
                        "title": section["title"],
                        "content": []
                    }
                    current_article["sections"].append(current_section)
                    continue

                # -------------------------
                # Body text
                # -------------------------
                if current_section:
                    current_section["content"].append({
                        "type": "text",
                        "value": text,
                        "page": page_no
                    })

            # -------------------------
            # Tables
            # -------------------------
            if current_section:
                for t in tables:
                    current_section["content"].append({
                        "type": "table",
                        "value": t,
                        "page": page_no
                    })

    if not document["document_title"]:
        document["document_title"] = default_title

    return document
