from fastapi import APIRouter, UploadFile, File, HTTPException,status
import shutil, os

from app.extractor import extract_pdf
from app.neo4j_client import Neo4jClient

router = APIRouter()

@router.post("/document")
def extract_document(file: UploadFile = File(...)):
    try:
        os.makedirs("uploads", exist_ok=True)
        path = f"uploads/{file.filename}"

        # Save uploaded file
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        try:
            document = extract_pdf(path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        articles = document.get("articles", [])

        if not articles:
            raise HTTPException(status_code=400, detail="No articles extracted from document")

        neo = Neo4jClient()
        neo.init_schema()

        # ✅ INSERT ONCE
        neo.insert_document_with_articles(document)

        return {
            "document_title": document.get("document_title"),
            "articles_inserted": len(articles)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unable to extract {str(e)}"
        )
