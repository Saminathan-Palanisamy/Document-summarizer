from fastapi import FastAPI
from app.routers.extract import router as extract_router
from app.routers.search import router as search_router

app = FastAPI(
    title="Project Summarizer"
)

app.include_router(extract_router, prefix="/extract", tags=["Extraction"])
app.include_router(search_router, prefix="/search", tags=["Search"])
print(app.routes)

@app.get("/")
def health_check():
    return {"status": "running"}
