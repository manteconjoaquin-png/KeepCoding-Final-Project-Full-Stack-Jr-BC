from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MovieBase(BaseModel):
    title: str = Field(min_length=1, max_length=250)
    year: int
    imdb_id: str = Field(min_length=1, max_length=20)
    poster: str | None = None
    plot: str | None = None

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        current_year = date.today().year
        if not 1895 <= value <= current_year:
            raise ValueError(f"El año debe estar entre 1895 y {current_year}.")
        return value


class RatingCreate(BaseModel):
    score: int = Field(ge=1, le=5)


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El comentario no puede estar vacío.")
        return normalized


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    created_at: datetime


class MovieResponse(MovieBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    average_rating: float = 0.0
    ratings_count: int = 0
    comments: list[CommentResponse] = Field(default_factory=list)
