# # extractor.py
# import pdfplumber
# import re
# import os
# from typing import List, Dict

# # =========================
# # Regex patterns
# # =========================

# # ARTICLE I Definitions 1
# ARTICLE_REGEX = re.compile(
#     r"^ARTICLE\s+([IVXLC\d]+)\s+(.+?)(?:\s+(\d+))?$",
#     re.IGNORECASE
# )

# # SECTION 1.1 Definitions 1
# SECTION_REGEX = re.compile(
#     r"^SECTION\s+(\d+\.\d+)\s+(.+?)(?:\s+(\d+))?$",
#     re.IGNORECASE
# )

# # Normalize whitespace
# def normalize_space(text: str) -> str:
#     return re.sub(r"\s+", " ", text).strip()

# # =========================
# # Step 1: Extract Articles from PDF
# # =========================
# def extract_articles(pdf: pdfplumber.PDF, max_pages: int = 15) -> List[Dict]:
#     """
#     Extracts articles and their starting pages.
#     Returns:
#         [
#             {
#                 "article_no": "ARTICLE I",
#                 "title": "Definitions",
#                 "start_page": 1
#             }
#         ]
#     """
#     articles = []

#     for page_index, page in enumerate(pdf.pages[:max_pages]):
#         text = page.extract_text() or ""
#         lines = [normalize_space(l) for l in text.split("\n") if l.strip()]

#         for line in lines:
#             m = ARTICLE_REGEX.match(line)
#             if m:
#                 roman_num = m.group(1).upper()
#                 title = normalize_space(m.group(2))
#                 start_page = int(m.group(3)) if m.group(3) else page_index + 1

#                 articles.append({
#                     "article_no": f"ARTICLE {roman_num}",
#                     "title": title,
#                     "start_page": start_page
#                 })
#     return articles

# # =========================
# # Step 2: Extract Sections & their content
# # =========================
# def extract_sections(pdf: pdfplumber.PDF, articles: List[Dict]) -> List[Dict]:
#     """
#     Build the structure:
#     [
#         {
#             "article_title": "ARTICLE I",
#             "display_name": "Definitions",
#             "sections": [
#                 {
#                     "section_id": "1.1",
#                     "title": "Definitions",
#                     "content": ["line1", "line2", ...]
#                 }
#             ]
#         }
#     ]
#     """
#     total_pages = len(pdf.pages)
#     results = []

#     # Sort articles by start_page
#     articles = sorted(articles, key=lambda x: x["start_page"])

#     for idx, art in enumerate(articles):
#         start_page = art["start_page"] - 1
#         end_page = articles[idx + 1]["start_page"] - 2 if idx + 1 < len(articles) else total_pages - 1

#         article_obj = {
#             "article_title": art["article_no"],
#             "display_name": art["title"],
#             "sections": []
#         }

#         current_section = None

#         for p in range(start_page, min(end_page + 1, total_pages)):
#             page = pdf.pages[p]
#             text = page.extract_text() or ""
#             lines = [normalize_space(l) for l in text.split("\n") if l.strip()]

#             for line in lines:
#                 sm = SECTION_REGEX.match(line)
#                 if sm:
#                     section_id = sm.group(1)
#                     title = normalize_space(sm.group(2))
#                     current_section = {
#                         "section_id": section_id,
#                         "title": title,
#                         "content": []
#                     }
#                     article_obj["sections"].append(current_section)
#                     continue

#                 # Skip repeated ARTICLE headers inside content
#                 if ARTICLE_REGEX.match(line):
#                     continue

#                 # Add content to current section
#                 if current_section:
#                     current_section["content"].append(line)

#         results.append(article_obj)

#     return results

# # =========================
# # Step 3: Main extraction function
# # =========================
# def extract_pdf(file_path: str) -> Dict:
#     """
#     Extract articles → sections → section content from a PDF.
#     Returns dict ready for Neo4j insertion.
#     """
#     document_title = os.path.splitext(os.path.basename(file_path))[0]

#     with pdfplumber.open(file_path) as pdf:
#         articles = extract_articles(pdf, max_pages=15)
#         if not articles:
#             raise ValueError("No articles found — cannot proceed")

#         articles_with_sections = extract_sections(pdf, articles)

#     return {
#         "document_title": document_title,
#         "articles": articles_with_sections
#     }

# # =========================
# # Quick test when running directly
# # =========================
# if __name__ == "__main__":
#     pdf_path = "ca_AMD.pdf"  # replace with your PDF
#     data = extract_pdf(pdf_path)
#     print(f"Document: {data['document_title']}")
#     for a in data["articles"]:
#         print(f"{a['article_title']} {a['display_name']}")
#         for s in a["sections"]:
#             print(f"  {s['section_id']} {s['title']} -> {len(s['content'])} lines")

import pdfplumber
import re
from collections import defaultdict
from app.neo4j_client import Neo4jClient
import os

neo4j = Neo4jClient()

# 🔴 CHANGE THIS TO YOUR PDF PATH
PDF_PATH = r"C:\Users\ib-69\Documents\My learnings_Python\Project summarizing\Project summarizing design 2\uploads\ca_AMD.pdf"

# How many first pages to scan for TOC
# TOC_PAGES = 5

ARTICLE_RE = re.compile(r"^ARTICLE\s+([IVXLC]+)\s+(.*)", re.IGNORECASE)
SECTION_RE = re.compile(r"^(?:SECTION\s+)?(\d+\.\d+)\s+(.*?)(?:\s+(\d+))?$", re.IGNORECASE)
PAGE_ONLY_RE = re.compile(r"^\d+$")


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


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

            # Check if this page looks like TOC
            toc_like = False
            for l in page_lines:
                if ARTICLE_RE.match(l) or SECTION_RE.match(l):
                    toc_like = True
                    break

            if toc_like:
                toc_pages_found += 1
                non_toc_pages_in_row = 0
                lines.extend(page_lines)
            else:
                non_toc_pages_in_row += 1
                # If we already started TOC and now 2 pages are non-TOC → stop
                if toc_pages_found > 0 and non_toc_pages_in_row >= 2:
                    break

    return lines



def parse_toc(lines):
    articles = {}
    current_article = None

    pending_section = None  # store section waiting for page number

    for line in lines:
        # Detect ARTICLE
        m_art = ARTICLE_RE.match(line)
        if m_art:
            roman = m_art.group(1)
            title = m_art.group(2).strip()
            current_article = f"ARTICLE {roman} {title}"
            articles[current_article] = []
            pending_section = None
            continue

        if not current_article:
            continue  # ignore anything before first ARTICLE

        # If previous section was waiting for page number
        if pending_section and PAGE_ONLY_RE.match(line):
            sec_no, sec_title = pending_section
            page = line
            articles[current_article].append((sec_no, sec_title, page))
            pending_section = None
            continue

        # Detect SECTION
        m_sec = SECTION_RE.match(line)
        if m_sec:
            sec_no = m_sec.group(1)
            sec_title = m_sec.group(2).strip().rstrip(".")
            page = m_sec.group(3)

            if page:
                articles[current_article].append((sec_no, sec_title, page))
                pending_section = None
            else:
                # Page number is probably on next line
                pending_section = (sec_no, sec_title)
            continue

        # If line doesn't match anything, ignore (TOC noise)
        continue

    return articles



def insert_document(doc_title: str):
    query = """
    MERGE (d:Document {title: $title})
    RETURN d
    """
    neo4j.run(query, {"title": doc_title})


def insert_article(doc_title: str, article_no: str, article_title: str, start_page: int):
    query = """
    MATCH (d:Document {title: $doc_title})
    MERGE (a:Article {article_no: $article_no})
    SET a.title = $article_title,
        a.start_page = $start_page
    MERGE (d)-[:HAS_ARTICLE]->(a)
    RETURN a
    """
    neo4j.run(query, {
        "doc_title": doc_title,
        "article_no": article_no,
        "article_title": article_title,
        "start_page": start_page
    })


def insert_section(article_no: str, section_no: str, section_title: str, start_page: int):
    query = """
    MATCH (a:Article {article_no: $article_no})
    MERGE (s:Section {section_no: $section_no})
    SET s.title = $section_title,
        s.start_page = $start_page
    MERGE (a)-[:HAS_SECTION]->(s)
    RETURN s
    """
    neo4j.run(query, {
        "article_no": article_no,
        "section_no": section_no,
        "section_title": section_title,
        "start_page": start_page
    })



def main():
    print("📄 Reading TOC from PDF...")
    lines = extract_toc_lines(PDF_PATH)

    articles = parse_toc(lines)

    print("\n================ TOC STRUCTURE ================\n")
    for article, sections in articles.items():
        print(article)
        for sec_no, title, page in sections:
            print(f"  {sec_no} {title} -> page {page}")
        print()

    print("🚀 Inserting TOC into Neo4j...")


    doc_title = os.path.splitext(os.path.basename(PDF_PATH))[0]
    neo4j.insert_toc_only(doc_title, articles)



    print("✅ Done. TOC inserted into Neo4j. No body content touched.")



if __name__ == "__main__":
    main()
