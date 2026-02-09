from fastapi import APIRouter, UploadFile, File, HTTPException, status
import os
import shutil
from fastapi.responses import JSONResponse
from app.extractor import insert_full_document  

router = APIRouter()


@router.post("/document")
def extract_document(file: UploadFile = File(...)):
    try:
        # uploads folder create pannum
        os.makedirs("uploads", exist_ok=True)

        file_path = os.path.join("uploads", file.filename)

        # uploaded file save pannum
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # unga existing function call
        insert_full_document(file_path)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
            "status": "success",
            "filename": file.filename,
            "message": "PDF extracted and inserted into Neo4j successfully"
        })

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
