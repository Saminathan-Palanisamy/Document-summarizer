import pdfplumber
import re
import os
from app.neo4j_client import Neo4jClient

neo4j = Neo4jClient()

# 🔴 PDF Path
PDF_PATH = r"C:\Users\ib-69\Documents\My learnings_Python\Project summarizing\Project summarizing design 2\uploads\ca_AMD.pdf"

# Regex
ARTICLE_RE = re.compile(r"^ARTICLE\s+([IVXLC]+)\s+(.*)", re.IGNORECASE)
SECTION_RE = re.compile(r"^(?:SECTION\s+)?(\d+\.\d+)\s+(.*)", re.IGNORECASE)
PAGE_ONLY_RE = re.compile(r"^\d+$")

# Chunk size (lines per chunk)
CHUNK_SIZE = 10


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


# ------------------- TOC PARSING -------------------
def extract_toc_lines(pdf_path, max_scan_pages=30):
    lines = []
    toc_pages_found = 0
    non_toc_pages_in_row = 0

    with pdfplumber.open(pdf_path) as pdf:
        for i in range(min(max_scan_pages, len(pdf.pages))):
            page = pdf.pages[i]
            text = page.extract_text()
            if not text:
                non_toc_pages_in_row += 1
                if non_toc_pages_in_row >= 2:
                    break
                continue

            page_lines = [normalize_line(l) for l in text.split("\n") if normalize_line(l)]

            toc_like = any(ARTICLE_RE.match(l) or SECTION_RE.match(l) for l in page_lines)
            if toc_like:
                toc_pages_found += 1
                non_toc_pages_in_row = 0
                lines.extend(page_lines)
            else:
                non_toc_pages_in_row += 1
                if toc_pages_found > 0 and non_toc_pages_in_row >= 2:
                    break

    return lines


def parse_toc(lines):
    articles = {}
    current_article = None
    pending_section = None

    for line in lines:
        m_art = ARTICLE_RE.match(line)
        if m_art:
            roman = m_art.group(1)
            title = m_art.group(2).strip()
            current_article = f"ARTICLE {roman} {title}"
            articles[current_article] = []
            pending_section = None
            continue

        if not current_article:
            continue

        if pending_section and PAGE_ONLY_RE.match(line):
            sec_no, sec_title = pending_section
            articles[current_article].append((sec_no, sec_title))
            pending_section = None
            continue

        m_sec = SECTION_RE.match(line)
        if m_sec:
            sec_no = m_sec.group(1)
            sec_title = re.sub(r"\s+\d+$", "", m_sec.group(2).strip().rstrip("."))
            articles[current_article].append((sec_no, sec_title))

    return articles


# ------------------- BODY-BASED SECTION EXTRACTION -------------------
def extract_sections_content_by_headers(pdf_path, toc_articles):
    """
    Reads full PDF text and splits content by real SECTION headers.
    Returns:
        {
            "ARTICLE I Something": [
                {"section_id": "1.1", "title": "...", "content": [chunks...]},
                ...
            ]
        }
    """

    # Prepare lookup for valid sections from TOC
    valid_sections = {}
    for article_name, sections in toc_articles.items():
        for sec_no, sec_title in sections:
            valid_sections[sec_no] = sec_title

    # Read full PDF lines
    all_lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = [normalize_line(l) for l in text.split("\n") if normalize_line(l)]
            all_lines.extend(lines)

    # Walk through lines and split by SECTION headers
    sections_content = {}
    current_section = None
    current_buffer = []

    section_header_re = re.compile(r"^SECTION\s+(\d+\.\d+)\s+(.*)", re.IGNORECASE)

    for line in all_lines:
        m = section_header_re.match(line)
        if m:
            sec_no = m.group(1)
            sec_title = m.group(2).strip()

            # Save previous section
            if current_section:
                sections_content[current_section]["lines"].extend(current_buffer)

            # Start new section only if it's in TOC
            if sec_no in valid_sections:
                current_section = sec_no
                sections_content[current_section] = {
                    "section_id": sec_no,
                    "title": valid_sections.get(sec_no, sec_title),
                    "lines": []
                }
                current_buffer = []
                # Add title line as first content line
                current_buffer.append(sec_title)
            else:
                # Unknown section header → ignore as splitter
                current_buffer.append(line)
        else:
            if current_section:
                current_buffer.append(line)

    # Save last section
    if current_section and current_section in sections_content:
        sections_content[current_section]["lines"].extend(current_buffer)

    # Chunking
    final_sections = {}
    for sec_no, data in sections_content.items():
        lines = data["lines"]
        full_text = " ".join(lines)

        final_sections[sec_no] = {
            "section_id": sec_no,
            "title": data["title"],
            "content": full_text
        }


    # Map back to articles
    article_map = {article: [] for article in toc_articles}

    for article_name, sections in toc_articles.items():
        for sec_no, sec_title in sections:
            if sec_no in final_sections:
                article_map[article_name].append(final_sections[sec_no])
            else:
                # Section exists in TOC but not found in body
                article_map[article_name].append({
                    "section_id": sec_no,
                    "title": sec_title,
                    "content": []
                })

    return article_map


# ------------------- INSERT INTO NEO4J -------------------
def insert_full_document(pdf_path):
    print("📄 Reading TOC from PDF...")
    toc_lines = extract_toc_lines(pdf_path)
    toc_articles = parse_toc(toc_lines)

    print("📑 Extracting section content using SECTION headers...")
    sections_content = extract_sections_content_by_headers(pdf_path, toc_articles)

    # Build document structure
    document_title = os.path.splitext(os.path.basename(pdf_path))[0]
    document = {
        "document_title": document_title,
        "articles": []
    }

    for article_name, sections in sections_content.items():
        parts = article_name.split(" ", 2)
        article_no = parts[1] if len(parts) > 1 else article_name
        display_name = parts[2] if len(parts) > 2 else article_name

        document["articles"].append({
            "article_title": article_no,
            "display_name": display_name,
            "sections": sections
        })

    print("🚀 Inserting full document into Neo4j...")
    neo4j.insert_document_with_articles(document)
    print("✅ Done. Document with section content inserted.")


