from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.database import Base, engine
from controllers.movie_controller import router as movie_router
import models.db_models  # noqa: F401

BASE_DIR = Path(__file__).resolve().parent
VIEWS_DIR = BASE_DIR / "views"

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CineLocal", version="1.0.0")
app.mount("/views", StaticFiles(directory=VIEWS_DIR), name="views")
app.include_router(movie_router)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    index_file = VIEWS_DIR / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=404, detail="No se encontró la interfaz web.")
    return FileResponse(index_file)
