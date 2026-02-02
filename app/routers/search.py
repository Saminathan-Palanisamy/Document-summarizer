from fastapi import APIRouter
from app.neo4j_client import Neo4jClient

router = APIRouter()

@router.post("/article-summary")
def search_article(payload: dict):
    name = payload["article_name"]
    neo = Neo4jClient()
    return neo.search_article(name)
