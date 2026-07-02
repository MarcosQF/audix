from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from audix.podcasts.enums import PodcastCategory
from audix.users.schemas import ResponseUser


class PodcastBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=10)
    category: PodcastCategory

class PodcastCreate(PodcastBase):
    pass

class PodcastUpdate(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=150)
    description: str | None = Field(None, min_length=10)
    category: PodcastCategory | None = None

class ListPodcast(BaseModel):
    quantity: int
    podcasts: list[PodcastResponse]

class PodcastResponse(PodcastBase):
    id: int
    image_url: str | None
    author: ResponseUser
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
