from fastapi import FastAPI
from app.routers import extract, search

app = FastAPI(title="Legal Document Extractor")

app.include_router(extract.router, prefix="/extract")
app.include_router(search.router, prefix="/search")


@app.get("/")
def health_check():
    return {"status": "running"}