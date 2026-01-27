# app/routers/extract.py

import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, status

from app.services.pdf_extractor import extract_pdf
from app.services.structure_parser import parse_structure
from app.services.chunker import chunk_document
from app.db.graph_store import GraphStore

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/document")
async def upload_document(file: UploadFile = File(...)):
    try:
        # ---------------------------
        # 1️⃣ Validate file type
        # ---------------------------
        filename = file.filename.lower()
        print("=> Validate file type")

        if not (filename.endswith(".pdf") or filename.endswith(".docx")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF or DOCX files are supported"
            )

        # ---------------------------
        # 2️⃣ Save file locally
        # ---------------------------
        file_path = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # ---------------------------
        # 3️⃣ Extract content
        # ---------------------------
        if filename.endswith(".pdf"):
            document = extract_pdf(file_path)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail= "DOCX support will be added next")
        
        print("in Extract content")

        # ---------------------------
        # 4️⃣ Parse → Chunk
        # ---------------------------
        document = parse_structure(document)
        document = chunk_document(document)

        if not document.get("articles"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="No structured content detected in document"
            )

        # ---------------------------
        # 5️⃣ Store in Neo4j
        # ---------------------------
        store = GraphStore()
        store.store_document(document)
        store.close()
        print("stored in graph")

        # ---------------------------
        # 6️⃣ Response
        # ---------------------------
        return {
            "status": "success",
            "document_title": document["document_title"],
            "articles_detected": len(document["articles"]),
            "message": "Document ingested successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"unable to extract: {str(e)}")
