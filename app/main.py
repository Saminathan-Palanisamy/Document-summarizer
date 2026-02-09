from fastapi import FastAPI,status
from app.routers import extract, search
from fastapi.responses import JSONResponse


app = FastAPI(title="Legal Document Extractor")

app.include_router(extract.router, prefix="/extract")
app.include_router(search.router, prefix="/search")


@app.get("/")
def health_check():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "running"})