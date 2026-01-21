from docx import Document

def extract_docx(file_path: str) -> dict:
    document = {
        "document_title": None,
        "articles": []
    }

    current_article = None
    current_subheading = None

    doc = Document(file_path)

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Set first non-empty paragraph as document title
        if not document["document_title"]:
            document["document_title"] = text
            continue

        # Heading detection
        if para.style.name.startswith("Heading 1"):
            current_article = {"article_title": text, "subheadings": []}
            document["articles"].append(current_article)
            current_subheading = None
            continue
        elif para.style.name.startswith("Heading 2") or para.style.name.startswith("Heading 3"):
            current_subheading = {"title": text, "content": []}
            if current_article:
                current_article["subheadings"].append(current_subheading)
            continue

        # Body text
        if current_subheading:
            current_subheading["content"].append({"type": "text", "value": text})

    return document
