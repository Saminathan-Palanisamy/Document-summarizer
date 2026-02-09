from fastapi import APIRouter, HTTPException, status
from app.neo4j_client import Neo4jClient
from app.groq_client import summarize_text
from fastapi.responses import JSONResponse

router = APIRouter()
neo4j = Neo4jClient()


@router.get("/article/{article_name}")
def get_article_summary(article_name: str):
    """
    Example:
    /article/ARTICLE V
    /article/General Loan Provisions
    """
    try:

        article = neo4j.get_article_with_sections_and_chunks(article_name)

        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        output = {
            "article_no": article["article_no"],
            "article_title": article["article_title"],
            "sections": []
        }

        print(f"📘 Found Article: {article['article_no']} - {article['article_title']}")

        for sec in article["sections"]:
            full_text = " ".join(sec["chunks"])
            print(f"🧩 Summarizing Section {sec['section_no']} ...")

            summary = summarize_text(full_text)

            output["sections"].append({
                "section_no": sec["section_no"],
                "section_title": sec["section_title"],
                "summary": summary
            })

        return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "output":output
                })

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unable to search{str(e)}")
