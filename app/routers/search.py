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
        article_name = query.article_name.strip()

        # 1️⃣ Fuzzy search for article title
        subheadings = neo_client.fuzzy_search_subheadings(article_name)
        print("search for subheading started")

        if not subheadings:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

        # 2️⃣ Aggregate chunks per subheading
        results = []
        for sub in subheadings:
            text = " ".join([c["text"] for c in sub.get("chunks", [])])

            # 3️⃣ Summarize using Groq LLM
            summary = groq.summarize(text)

            results.append({
                "title": sub["title"],
                "summary": summary
            })
        print("summarizing finished=>")
        print("results------",results)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
            "document_title": subheadings[0]["document_title"],
            "article_title": subheadings[0]["article_title"],
            "subheadings": results
        })
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"unable to search: {str(e)}")
