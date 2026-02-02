from neo4j import GraphDatabase
from app.config import settings
import uuid

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
        with self.driver.session(database=self.database) as session:
            session.run("""
            CREATE FULLTEXT INDEX articleIndex IF NOT EXISTS
            FOR (a:Article)
            ON EACH [a.article_title]
            """)

    def insert_document_with_articles(self, document: dict):
        with self.driver.session(database=self.database) as session:
            # Create / merge Document
            session.run(
                """
                MERGE (d:Document {title: $title})
                """,
                {"title": document.get("document_title", "Unknown Document")}
            )
            print("extraction work started...")

            for article in document.get("articles", []):
                # Merge Article
                session.run(
                    """
                    MERGE (a:Article {article_title: $article_title})
                    SET a.display_name = $display_name
                    WITH a
                    MATCH (d:Document {title: $doc_title})
                    MERGE (d)-[:HAS_ARTICLE]->(a)
                    """,
                    {
                        "article_title": article["article_title"],
                        "display_name": article["display_name"],
                        "doc_title": document.get("document_title", "Unknown Document")
                    }
                )

                # Insert sections + chunks (reuse your existing logic)
                for sec in article.get("sections", []):
                    session.run(
                        """
                        MATCH (a:Article {article_title: $article_title})
                        MERGE (s:Section {section_id: $section_id, article_title: $article_title})
                        SET s.title = $title
                        MERGE (a)-[:HAS_SECTION]->(s)
                        """,
                        {
                            "article_title": article["article_title"],
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
                            MATCH (s:Section {section_id: $section_id, article_title: $article_title})
                            CREATE (c:Chunk {
                                idx: $idx,
                                type: $type,
                                text: $text,
                                page: $page
                            })
                            MERGE (s)-[:HAS_CHUNK]->(c)
                            """,
                            {
                                "article_title": article["article_title"],
                                "section_id": sec["section_id"],
                                "idx": idx,
                                "type": chunk_type,
                                "text": text,
                                "page": page,
                            }
                        )


    def insert_article_graph(self, article: dict):
        cypher_article = """
        MERGE (a:Article {article_title: $article_title})
        SET a.display_name = $display_name
        RETURN a
        """

        with self.driver.session(database=self.database) as session:
            session.run(
                cypher_article,
                {
                    "article_title": article["article_title"],
                    "display_name": article["display_name"],
                },
            )

            for sec in article.get("sections", []):
                session.run(
                    """
                    MATCH (a:Article {article_title: $article_title})
                    MERGE (s:Section {section_id: $section_id, article_title: $article_title})
                    SET s.title = $title
                    MERGE (a)-[:HAS_SECTION]->(s)
                    """,
                    {
                        "article_title": article["article_title"],
                        "section_id": sec["section_id"],
                        "title": sec.get("title", ""),
                    },
                )

                # 🔥 HERE is the important change: use "content", not "chunks"
                for idx, item in enumerate(sec.get("content", [])):
                    # If extractor stored plain strings
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
                        MATCH (s:Section {section_id: $section_id, article_title: $article_title})
                        CREATE (c:Chunk {
                            idx: $idx,
                            type: $type,
                            text: $text,
                            page: $page
                        })
                        MERGE (s)-[:HAS_CHUNK]->(c)
                        """,
                        {
                            "article_title": article["article_title"],
                            "section_id": sec["section_id"],
                            "idx": idx,
                            "type": chunk_type,
                            "text": text,
                            "page": page,
                        },
                    )



    def search_article(self, article_name):
        with self.driver.session(database=self.database) as session:
            result = session.run("""
            CALL db.index.fulltext.queryNodes('articleIndex', $q)
            YIELD node
            RETURN node.article_title AS title, node.display_name AS display
            """, q=article_name)
            return [r.data() for r in result]
    
