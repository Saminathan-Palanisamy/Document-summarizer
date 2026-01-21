# app/db/neo4j_client.py
from neo4j import GraphDatabase
from app.config import settings


class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
        )
        self.database = settings.NEO4J_DATABASE

    def close(self):
        self.driver.close()

    def run_query(self, query: str, params: dict = None):
        with self.driver.session(database=self.database) as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    # -------------------------
    # SCHEMA INITIALIZATION
    # -------------------------
    def init_schema(self):
        queries = [
            # Full-text index for fuzzy article search (Neo4j 5 syntax)
            """
            CREATE FULLTEXT INDEX articleIndex IF NOT EXISTS
            FOR (a:Article)
            ON EACH [a.title]
            """
        ]

        with self.driver.session(database=self.database) as session:
            for q in queries:
                session.run(q)

        print("✅ Neo4j schema & indexes initialized")

    # -------------------------
    # Fuzzy search subheadings
    # -------------------------
    def fuzzy_search_subheadings(self, article_name: str):
        """
        Returns all subheadings + chunks for a given article name (fuzzy search)
        Compatible with Neo4j 5+ fulltext index syntax
        """
        query = """
        MATCH (a:Article)-[:HAS_SUBHEADING]->(s:Subheading)-[:HAS_CHUNK]->(c:Chunk)
        WHERE a.title CONTAINS $name
        RETURN a.title AS article_title,
               a.document_title AS document_title,
               s.title AS subheading_title,
               collect({text: c.text, index: c.index}) AS chunks
        ORDER BY s.title
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, name=article_name)
            subheadings = []
            for record in result:
                subheadings.append({
                    "document_title": record["document_title"],
                    "article_title": record["article_title"],
                    "title": record["subheading_title"],
                    "chunks": record["chunks"]
                })
        return subheadings
