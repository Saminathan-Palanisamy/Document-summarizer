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
        query = """
        MATCH (a:Article)-[:HAS_SECTION]->(s:Section)-[:HAS_CHUNK]->(c:Chunk)
        WHERE a.title = $article
        RETURN
        a.title AS article_title,
        s.section_id AS section_id,
        s.title AS section_title,
        collect(c.text) AS chunks
        ORDER BY s.section_id
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, article=article_name)

            subheadings = []
            for record in result:
                subheadings.append({
                    "article_title": record["article_title"],
                    "title": record["section_title"],
                    "chunks": [{"text": t} for t in record["chunks"]]
                })

        return subheadings

    
    def search_section(
        self,
        article: str = None,
        search_text: str = None,
        section_id: str = None
    ):
        cypher = """
        MATCH (a:Article)-[:HAS_SECTION]->(s:Section)-[:HAS_CHUNK]->(c:Chunk)
        WHERE
        ($article IS NULL OR a.title = $article)
        AND (
                ($section_id IS NOT NULL AND s.section_id = $section_id)
            OR ($search_text IS NOT NULL AND toLower(s.title) CONTAINS toLower($search_text))
        )
        RETURN
            a.title AS article,
            s.section_id AS section_id,
            s.title AS title,
            collect(c.text) AS content
        ORDER BY s.section_id
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                cypher,
                article=article,
                search_text=search_text,
                section_id=section_id
            )

            return [r.data() for r in result]

