# app/services/chunker.py

from typing import List, Dict
import tiktoken


# -----------------------------
# Token utilities
# -----------------------------

def _get_tokenizer():
    """
    Use OpenAI-compatible tokenizer (works fine for Groq models too).
    """
    return tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    enc = _get_tokenizer()
    return len(enc.encode(text))


# -----------------------------
# Core chunker
# -----------------------------

def chunk_subheading(
    subheading: Dict,
    max_tokens: int = 1200
) -> List[Dict]:
    """
    Chunk content of ONE subheading safely.
    """

    chunks = []
    current_chunk = ""
    chunk_index = 1

    for item in subheading.get("content", []):

        if item["type"] == "table":
            table_text = "\n[TABLE]\n" + item["value"] + "\n[/TABLE]\n"

            # If table itself exceeds limit, force its own chunk
            if _count_tokens(table_text) > max_tokens:
                if current_chunk:
                    chunks.append({
                        "chunk_index": chunk_index,
                        "text": current_chunk.strip()
                    })
                    chunk_index += 1
                    current_chunk = ""

                chunks.append({
                    "chunk_index": chunk_index,
                    "text": table_text.strip()
                })
                chunk_index += 1
                continue

            # Else attach table to current chunk
            if _count_tokens(current_chunk + table_text) > max_tokens:
                chunks.append({
                    "chunk_index": chunk_index,
                    "text": current_chunk.strip()
                })
                chunk_index += 1
                current_chunk = table_text
            else:
                current_chunk += table_text

        else:
            text = item["value"] + "\n"

            if _count_tokens(current_chunk + text) > max_tokens:
                chunks.append({
                    "chunk_index": chunk_index,
                    "text": current_chunk.strip()
                })
                chunk_index += 1
                current_chunk = text
            else:
                current_chunk += text

    if current_chunk.strip():
        chunks.append({
            "chunk_index": chunk_index,
            "text": current_chunk.strip()
        })

    return chunks


# -----------------------------
# Document-level chunking
# -----------------------------

def chunk_document(document: Dict) -> Dict:
    """
    Chunk entire parsed document.
    """

    for article in document.get("articles", []):
        for sub in article.get("subheadings", []):
            sub["chunks"] = chunk_subheading(sub)
            sub.pop("content", None)

    return document