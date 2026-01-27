# app/db/graph_store.py

from neo4j import GraphDatabase
from app.config import settings
import re


class GraphStore:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    # -------------------------
    # Create document hierarchy
    # -------------------------
    def store_document(self, document: dict):
        with self.driver.session(database=settings.NEO4J_DATABASE) as session:

            # -------------------------
            # Document
            # -------------------------
            doc_title = document.get("document_title", "Untitled")
            session.execute_write(self._create_document, doc_title)

            # -------------------------
            # Articles → Sections → Chunks
            # -------------------------
            for article in document.get("articles", []):
                raw_title = article.get("article_title", "")

                # Example:
                # "ARTICLE IV General Loan Provisions 46"
                match = re.match(
                    r"^(ARTICLE\s+[IVX]+)\s+(.*?)(?:\s+\d+)?$",
                    raw_title,
                    re.IGNORECASE
                )

                if match:
                    article_no = match.group(1).upper()
                    article_title = match.group(2).strip()
                else:
                    article_no = raw_title.upper()
                    article_title = raw_title.strip()

                # Create Article
                session.execute_write(
                    self._create_article,
                    doc_title,
                    article_no,
                    article_title
                )

                # Sections
                for section in article.get("sections", []):
                    session.execute_write(
                        self._create_section,
                        doc_title,
                        article_title,
                        section
                    )

                    # Chunks
                    for chunk in section.get("chunks", []):
                        session.execute_write(
                            self._create_chunk,
                            doc_title,
                            article_title,
                            section,
                            chunk
                        )

    # -------------------------
    # Transactions
    # -------------------------

    @staticmethod
    def _create_document(tx, doc_title):
        tx.run(
            """
            MERGE (d:Document {title: $doc_title})
            """,
            doc_title=doc_title
        )

    @staticmethod
    def _create_article(tx, doc_title, article_no, article_title):
        tx.run(
            """
            MATCH (d:Document {title: $doc_title})
            MERGE (a:Article {
                article_no: $article_no,
                title: $article_title
            })
            MERGE (d)-[:HAS_ARTICLE]->(a)
            """,
            doc_title=doc_title,
            article_no=article_no,
            article_title=article_title
        )

    @staticmethod
    def _create_section(tx, doc_title, article_title, section):
        tx.run(
            """
            MATCH (d:Document {title: $doc_title})
                -[:HAS_ARTICLE]->(a:Article {title: $article_title})
            MERGE (s:Section {
                section_id: $section_id,
                title: $title
            })
            MERGE (a)-[:HAS_SECTION]->(s)
            """,
            doc_title=doc_title,
            article_title=article_title,
            section_id=section["section_id"],
            title=section["title"]
        )

    @staticmethod
    def _create_chunk(tx, doc_title, article_title, section, chunk):
        tx.run(
            """
            MATCH (d:Document {title: $doc_title})
                -[:HAS_ARTICLE]->(a:Article {title: $article_title})
                -[:HAS_SECTION]->(s:Section {section_id: $section_id})
            CREATE (c:Chunk {
                text: $text,
                index: $index
            })
            MERGE (s)-[:HAS_CHUNK]->(c)
            """,
            doc_title=doc_title,
            article_title=article_title,
            section_id=section["section_id"],
            text=chunk["text"],
            index=chunk["chunk_index"]
        )
