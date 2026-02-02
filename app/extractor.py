
import pdfplumber
import re
import os
from typing import List, Dict

# =========================
# Regex patterns
# =========================

TOC_TITLE_REGEX = re.compile(r"^(TABLE OF CONTENTS|CONTENTS)$", re.IGNORECASE)

# Example:
# ARTICLE II. THE CREDITS ........ 38
TOC_ARTICLE_REGEX = re.compile(
    r"^ARTICLE\s+([IVXLC\d]+)\.?\s+(.+?)\s+(\d+)$",
    re.IGNORECASE
)

# Section headers like:
# 2.01 The Commitments
SECTION_REGEX = re.compile(
    r"^(?:SECTION\s+)?(\d+(?:\.\d+)+)\s*(.*)$",
    re.IGNORECASE
)

ARTICLE_HEADER_REGEX = re.compile(
    r"^ARTICLE\s+([IVXLC\d]+)\.?\s*(.*)$",
    re.IGNORECASE
)

# =========================
# Helpers
# =========================

def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

# =========================
# Step 1: Extract TOC Articles
# =========================

def extract_toc(pdf: pdfplumber.PDF, max_pages: int = 10) -> List[Dict]:
    """
    Returns list of:
    [
      {
        "article_no": "ARTICLE I",
        "display_name": "DEFINITIONS",
        "start_page": 1
      },
      ...
    ]
    """
    articles = []
    inside_toc = False

    for page_index, page in enumerate(pdf.pages[:max_pages]):
        text = page.extract_text() or ""
        lines = [normalize_space(l) for l in text.split("\n") if l.strip()]

        for line in lines:
            if TOC_TITLE_REGEX.match(line):
                inside_toc = True
                continue

            if not inside_toc:
                continue

            # Stop if TOC clearly ended (first real section appears)
            if line.upper().startswith("1.01 "):
                return articles

            m = TOC_ARTICLE_REGEX.match(line)
            if m:
                roman_or_num = m.group(1).upper()
                title = normalize_space(m.group(2))
                page_no = int(m.group(3))

                articles.append({
                    "article_no": f"ARTICLE {roman_or_num}",
                    "display_name": title,
                    "start_page": page_no
                })

    return articles

# =========================
# Step 2: Extract content by article ranges
# =========================

def extract_articles_content(pdf: pdfplumber.PDF, toc_articles: List[Dict]) -> List[Dict]:
    """
    Build:
    [
      {
        "article_title": "ARTICLE I",
        "display_name": "DEFINITIONS",
        "sections": [
            {
              "section_id": "1.01",
              "title": "Defined Terms",
              "content": ["text...", "text..."]
            }
        ]
      }
    ]
    """

    results = []

    # Sort by start_page
    toc_articles = sorted(toc_articles, key=lambda x: x["start_page"])

    total_pages = len(pdf.pages)

    for idx, art in enumerate(toc_articles):
        start_page = art["start_page"] - 1  # pdfplumber is 0-based
        if idx + 1 < len(toc_articles):
            end_page = toc_articles[idx + 1]["start_page"] - 2
        else:
            end_page = total_pages - 1

        article_obj = {
            "article_title": art["article_no"],
            "display_name": art["display_name"],
            "sections": []
        }

        current_section = None

        for p in range(start_page, min(end_page + 1, total_pages)):
            page = pdf.pages[p]
            text = page.extract_text() or ""
            if "TABLE OF CONTENTS" in text.upper():
                continue
            lines = [normalize_space(l) for l in text.split("\n") if l.strip()]

            for line in lines:
                # Detect section header
                sm = SECTION_REGEX.match(line)
                if sm:
                    section_id = sm.group(1)
                    title = normalize_space(sm.group(2) or "")

                    current_section = {
                        "section_id": section_id,
                        "title": title,
                        "content": []
                    }
                    print("FOUND SECTION:", section_id, title)
                    article_obj["sections"].append(current_section)
                    continue

                # Skip repeated ARTICLE headers inside body
                if ARTICLE_HEADER_REGEX.match(line):
                    continue

                # Normal body text
                if current_section:
                    current_section["content"].append(line)

        results.append(article_obj)

    return results

# =========================
# Step 3: Main API function
# =========================

def extract_pdf(file_path: str) -> Dict:
    document_title = os.path.splitext(os.path.basename(file_path))[0]

    with pdfplumber.open(file_path) as pdf:
        toc_articles = extract_toc(pdf, max_pages=15)

        if not toc_articles:
            raise ValueError("TOC not found — cannot proceed safely")

        articles = extract_articles_content(pdf, toc_articles)

    return {
        "document_title": document_title,
        "articles": articles
    }
