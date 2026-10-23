import os
import re
from pathlib import Path

import httpx
from dotenv import dotenv_values, load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from config.database import get_db
from models.db_models import Comment, Movie, Rating
from models.schemas import (
    CommentCreate,
    MovieBase,
    MovieResponse,
    RatingCreate,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
OMDB_URL = "https://www.omdbapi.com?"

router = APIRouter(prefix="/api/movies", tags=["movies"])


def _get_omdb_api_key() -> str | None:
    return os.getenv("OMDB_API_KEY") or dotenv_values(PROJECT_ROOT / ".env").get(
        "OMDB_API_KEY"
    )


def _year_from_omdb(value: str | None) -> int | None:
    match = re.match(r"\s*(\d{4})", value or "")
    if not match:
        return None

    try:
        return MovieBase(
            title="Year validation",
            year=int(match.group(1)),
            imdb_id="tt0000000",
        ).year
    except ValueError:
        return None


def _movie_response(movie: Movie, db: Session) -> MovieResponse:
    average, count = (
        db.query(func.avg(Rating.score), func.count(Rating.id))
        .filter(Rating.movie_id == movie.id)
        .one()
    )
    return MovieResponse(
        id=movie.id,
        imdb_id=movie.imdb_id,
        title=movie.title,
        year=movie.year,
        poster=movie.poster,
        plot=movie.plot,
        average_rating=round(float(average), 2) if average is not None else 0.0,
        ratings_count=count,
        comments=movie.comments,
    )


async def _omdb_get(params: dict[str, str]) -> dict:
    api_key = _get_omdb_api_key()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configura OMDB_API_KEY en el archivo .env para buscar películas.",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                OMDB_URL,
                params={**params, "apikey": api_key},
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="OMDb tardó demasiado en responder.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="No se pudo conectar con OMDb.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="OMDb devolvió una respuesta inválida.") from exc


@router.get("", response_model=list[MovieResponse])
async def search_movies(
    title: str = Query(min_length=1, max_length=100),
    year: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[MovieResponse]:
    params = {"s": title.strip(), "type": "movie"}
    if year is not None:
        params["y"] = str(year)
    try:
        data = await _omdb_get(params)
    except HTTPException:
        local_query = db.query(Movie).filter(Movie.title.ilike(f"%{title}%"))
        if year is not None:
            local_query = local_query.filter(Movie.year == year)
        return [_movie_response(movie, db) for movie in local_query.all()]

    if data.get("Response") == "False":
        if "not found" in data.get("Error", "").lower():
            return []
        raise HTTPException(status_code=400, detail=data.get("Error", "Búsqueda inválida."))

    results: list[MovieResponse] = []
    for item in data.get("Search", []):
        year = _year_from_omdb(item.get("Year"))
        imdb_id = item.get("imdbID")
        title = (item.get("Title") or "").strip()
        if year is None or not imdb_id or not title:
            continue

        poster = item.get("Poster")
        movie_data = MovieBase(
            title=title[:250],
            year=year,
            imdb_id=imdb_id,
            poster=poster if poster and poster != "N/A" else None,
        )
        movie = db.query(Movie).filter(Movie.imdb_id == movie_data.imdb_id).first()
        if movie is None:
            movie = Movie(**movie_data.model_dump())
            db.add(movie)
            try:
                db.commit()
                db.refresh(movie)
            except Exception:
                db.rollback()
                movie = db.query(Movie).filter(Movie.imdb_id == movie_data.imdb_id).first()
                if movie is None:
                    raise
        results.append(_movie_response(movie, db))

    return results


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(movie_id: int, db: Session = Depends(get_db)) -> MovieResponse:
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Película no encontrada.")

    if _get_omdb_api_key():
        try:
            data = await _omdb_get({"i": movie.imdb_id, "plot": "full"})
            if data.get("Response") == "True" and data.get("Plot") not in (None, "N/A"):
                movie.plot = data["Plot"]
                db.commit()
                db.refresh(movie)
        except HTTPException:
            db.rollback()

    return _movie_response(movie, db)


@router.post("/{movie_id}/rate", response_model=MovieResponse)
def rate_movie(
    movie_id: int,
    payload: RatingCreate,
    db: Session = Depends(get_db),
) -> MovieResponse:
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Película no encontrada.")

    db.add(Rating(movie_id=movie_id, score=payload.score))
    db.commit()
    return _movie_response(movie, db)


@router.post("/{movie_id}/comment", response_model=MovieResponse)
def comment_movie(
    movie_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
) -> MovieResponse:
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Película no encontrada.")

    db.add(Comment(movie_id=movie_id, text=payload.text))
    db.commit()
    db.refresh(movie)
    return _movie_response(movie, db)
