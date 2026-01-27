from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.db.neo4j_client import Neo4jClient
from app.db.graph_store import GraphStore
from app.config import settings
from app.llm.groq_client import GroqClient
from fastapi.responses import JSONResponse
router = APIRouter()

# -----------------------------
# Request Model
# -----------------------------
class ArticleQuery(BaseModel):
    article_name: str


# -----------------------------
# Initialize Clients
# -----------------------------
neo_client = Neo4jClient()
groq = GroqClient(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
store = GraphStore()


# -----------------------------
# Router Endpoint
# -----------------------------

@router.post("/article-summary")
async def get_article_summary(query: ArticleQuery):
    try:
        user_query = query.article_name.strip()

        results = neo_client.search_section(
            article=None,
            search_text=user_query
        )

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found"
            )

        summaries = []
        for r in results:
            text = " ".join(r["content"])
            summary = groq.summarize(text)

            summaries.append({
                "section_id": r["section_id"],
                "title": r["title"],
                "summary": summary
            })

        return {
            "article": results[0]["article"],
            "sections": summaries
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"unable to search: {str(e)}")
