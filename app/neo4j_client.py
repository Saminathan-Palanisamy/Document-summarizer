from neo4j import GraphDatabase
from app.config import settings


class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        )
        self.database = settings.NEO4J_DATABASE

    def close(self):
        self.driver.close()

    def init_schema(self):
        """Create fulltext index for articles"""
        with self.driver.session(database=self.database) as session:
            session.run("""
            CREATE FULLTEXT INDEX articleIndex IF NOT EXISTS
            FOR (a:Article)
            ON EACH [a.title]
            """)

    # ------------------- TOC INSERTION -------------------
    def insert_toc_only(self, document_title: str, articles: dict):
        """
        Insert only TOC (Document -> Articles -> Sections) into Neo4j.
        articles: {
            "ARTICLE I Definitions 1": [
                ("1.1", "Definitions", "1"),
                ("1.2", "Other Definitions", "31")
            ]
        }
        """
        with self.driver.session(database=self.database) as session:
            # Merge Document
            session.run(
                "MERGE (d:Document {title: $title})",
                {"title": document_title}
            )

            for article_name, sections in articles.items():
                # Article number is first token, display_name is the rest
                parts = article_name.split(" ", 2)
                article_no = parts[1] if len(parts) > 1 else article_name
                display_name = parts[2] if len(parts) > 2 else article_name

                # Merge Article
                session.run(
                    """
                    MATCH (d:Document {title: $doc_title})
                    MERGE (a:Article {article_no: $article_no})
                    SET a.title = $display_name
                    MERGE (d)-[:HAS_ARTICLE]->(a)
                    """,
                    {
                        "doc_title": document_title,
                        "article_no": article_no,
                        "display_name": display_name
                    }
                )

                for sec_no, sec_title, page in sections:
                    # Merge Section
                    session.run(
                        """
                        MATCH (a:Article {article_no: $article_no})
                        MERGE (s:Section {section_no: $section_no})
                        SET s.title = $section_title,
                            s.start_page = $start_page
                        MERGE (a)-[:HAS_SECTION]->(s)
                        """,
                        {
                            "article_no": article_no,
                            "section_no": sec_no,
                            "section_title": sec_title,
                            "start_page": int(page) if page and page.isdigit() else None
                        }
                    )

    # ------------------- FULL DOCUMENT INSERTION -------------------
    def insert_document_with_articles(self, document: dict):
        """
        Insert full document with articles -> sections -> chunks
        """
        with self.driver.session(database=self.database) as session:
            # Merge Document
            session.run(
                "MERGE (d:Document {title: $title})",
                {"title": document.get("document_title", "Unknown Document")}
            )

            for article in document.get("articles", []):
                # Merge Article
                session.run(
                    """
                    MATCH (d:Document {title: $doc_title})
                    MERGE (a:Article {article_no: $article_no})
                    SET a.title = $display_name
                    MERGE (d)-[:HAS_ARTICLE]->(a)
                    """,
                    {
                        "doc_title": document.get("document_title", "Unknown Document"),
                        "article_no": article["article_title"],
                        "display_name": article["display_name"]
                    }
                )

                # Sections + Chunks
                for sec in article.get("sections", []):
                    session.run(
                        """
                        MATCH (a:Article {article_no: $article_no})
                        MERGE (s:Section {section_no: $section_id})
                        SET s.title = $title
                        MERGE (a)-[:HAS_SECTION]->(s)
                        """,
                        {
                            "article_no": article["article_title"],
                            "section_id": sec["section_id"],
                            "title": sec.get("title", "")
                        }
                    )

                    for idx, item in enumerate(sec.get("content", [])):
                        if isinstance(item, str):
                            chunk_type = "text"
                            text = item
                            page = None
                        else:
                            chunk_type = item.get("type", "text")
                            text = item.get("value", "")
                            page = item.get("page", None)

                        session.run(
                            """
                            MATCH (s:Section {section_no: $section_id})
                            CREATE (c:Chunk {
                                idx: $idx,
                                type: $type,
                                text: $text,
                                page: $page
                            })
                            MERGE (s)-[:HAS_CHUNK]->(c)
                            """,
                            {
                                "section_id": sec["section_id"],
                                "idx": idx,
                                "type": chunk_type,
                                "text": text,
                                "page": page
                            }
                        )

    # ------------------- SEARCH -------------------
    def search_article(self, article_name):
        with self.driver.session(database=self.database) as session:
            result = session.run("""
            CALL db.index.fulltext.queryNodes('articleIndex', $q)
            YIELD node
            RETURN node.article_no AS article_no, node.title AS title
            """, q=article_name)
            return [r.data() for r in result]
