# app/db/graph_store.py

from neo4j import GraphDatabase
from app.config import settings


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
            doc_title = document.get("document_title", "Untitled")
            session.execute_write(self._create_document, doc_title)

            for article in document.get("articles", []):
                art_title = article.get("article_title", "General")
                session.execute_write(self._create_article, doc_title, art_title)

                for sub in article.get("subheadings", []):
                    sub_title = sub.get("title", "Untitled")
                    session.execute_write(
                        self._create_subheading,
                        doc_title,
                        art_title,
                        sub_title
                    )

                    for chunk in sub.get("chunks", []):
                        session.execute_write(
                            self._create_chunk,
                            doc_title,
                            art_title,
                            sub_title,
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
    def _create_article(tx, doc_title, art_title):
        tx.run(
            """
            MATCH (d:Document {title: $doc_title})
            MERGE (a:Article {title: $art_title})
            MERGE (d)-[:HAS_ARTICLE]->(a)
            """,
            doc_title=doc_title,
            art_title=art_title
        )

    @staticmethod
    def _create_subheading(tx, doc_title, art_title, sub_title):
        tx.run(
            """
            MATCH (d:Document {title: $doc_title})
                  -[:HAS_ARTICLE]->(a:Article {title: $art_title})
            MERGE (s:Subheading {title: $sub_title})
            MERGE (a)-[:HAS_SUBHEADING]->(s)
            """,
            doc_title=doc_title,
            art_title=art_title,
            sub_title=sub_title
        )

    @staticmethod
    def _create_chunk(tx, doc_title, art_title, sub_title, chunk):
        tx.run(
            """
            MATCH (d:Document {title: $doc_title})
                  -[:HAS_ARTICLE]->(a:Article {title: $art_title})
                  -[:HAS_SUBHEADING]->(s:Subheading {title: $sub_title})
            MERGE (c:Chunk {text: $text, index: $index})
            MERGE (s)-[:HAS_CHUNK]->(c)
            """,
            text=chunk.get("text", ""),
            index=chunk.get("chunk_index", 1),
            doc_title=doc_title,
            art_title=art_title,
            sub_title=sub_title
        )
