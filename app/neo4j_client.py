# # app/neo4j_client.py
# from neo4j import GraphDatabase
# from app.config import settings

# class Neo4jClient:
#     def __init__(self):
#         self.driver = GraphDatabase.driver(
#             settings.NEO4J_URI,
#             auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
#         )
#         self.database = settings.NEO4J_DATABASE

#     def close(self):
#         self.driver.close()

#     def init_schema(self):
#         with self.driver.session(database=self.database) as session:
#             session.run("""
#             CREATE FULLTEXT INDEX IF NOT EXISTS articleIndex
#             FOR (a:Article)
#             ON EACH [a.title]
#             """)

#     def insert_document_with_articles(self, document: dict):
#         """
#         Insert Document -> Articles -> Sections -> Chunks
#         """
#         with self.driver.session(database=self.database) as session:
#             # Merge document
#             session.run(
#                 "MERGE (d:Document {title: $title})",
#                 {"title": document.get("document_title", "Unknown Document")}
#             )

#             for article in document.get("articles", []):
#                 # Merge Article
#                 session.run(
#                     """
#                     MERGE (a:Article {article_no: $article_no})
#                     SET a.title = $article_title, a.start_page = $start_page
#                     WITH a
#                     MATCH (d:Document {title: $doc_title})
#                     MERGE (d)-[:HAS_ARTICLE]->(a)
#                     """,
#                     {
#                         "article_no": article["article_title"],
#                         "article_title": article["display_name"],
#                         "start_page": article.get("start_page", 0),
#                         "doc_title": document.get("document_title", "Unknown Document")
#                     }
#                 )

#                 for sec in article.get("sections", []):
#                     # Merge Section
#                     session.run(
#                         """
#                         MATCH (a:Article {article_no: $article_no})
#                         MERGE (s:Section {section_no: $section_id})
#                         SET s.title = $title, s.start_page = $start_page
#                         MERGE (a)-[:HAS_SECTION]->(s)
#                         """,
#                         {
#                             "article_no": article["article_title"],
#                             "section_id": sec["section_id"],
#                             "title": sec["title"],
#                             "start_page": sec.get("start_page", 0)
#                         }
#                     )

#                     # Insert Chunks (line by line content)
#                     for idx, line in enumerate(sec.get("content", [])):
#                         session.run(
#                             """
#                             MATCH (s:Section {section_no: $section_id})
#                             CREATE (c:Chunk {idx: $idx, text: $text})
#                             MERGE (s)-[:HAS_CHUNK]->(c)
#                             """,
#                             {
#                                 "section_id": sec["section_id"],
#                                 "idx": idx,
#                                 "text": line
#                             }
#                         )

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
        
    def insert_toc_only(self, document_title: str, articles: dict):
        """
        articles format:
        {
          "ARTICLE I Definitions": [
              ("1.1", "Definitions", "1"),
              ("1.2", "Other Definitions", "31"),
          ],
          ...
        }
        """

        with self.driver.session(database=self.database) as session:
            # Create / merge Document
            session.run(
                """
                MERGE (d:Document {title: $title})
                """,
                {"title": document_title},
            )

            for article_full_title, sections in articles.items():
                # Split: "ARTICLE I Definitions" -> "ARTICLE I", "Definitions"
                parts = article_full_title.split(" ", 2)
                if len(parts) >= 3:
                    article_no = parts[0] + " " + parts[1]   # ARTICLE I
                    article_title = parts[2]                 # Definitions
                else:
                    article_no = article_full_title
                    article_title = article_full_title

                # Merge Article
                session.run(
                    """
                    MATCH (d:Document {title: $doc_title})
                    MERGE (a:Article {article_no: $article_no})
                    SET a.title = $article_title
                    MERGE (d)-[:HAS_ARTICLE]->(a)
                    """,
                    {
                        "doc_title": document_title,
                        "article_no": article_no,
                        "article_title": article_title,
                    },
                )

                # Insert Sections
                for sec_no, sec_title, page in sections:
                    session.run(
                        """
                        MATCH (a:Article {article_no: $article_no})
                        MERGE (s:Section {section_no: $section_no, article_no: $article_no})
                        SET s.title = $section_title,
                            s.start_page = toInteger($page)
                        MERGE (a)-[:HAS_SECTION]->(s)
                        """,
                        {
                            "article_no": article_no,
                            "section_no": sec_no,
                            "section_title": sec_title,
                            "page": page,
                        },
                    )
