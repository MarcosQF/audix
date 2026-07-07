from pydantic import BaseModel

from audix.podcasts.schemas import PodcastResponse
from audix.shared.types import StrippedString


class EpisodeResponse(BaseModel):
    id: int
    title: str
    description: str
    episode_number: int
    audio_url: str | None = None
    image_url: str | None = None
    duration: int | None = None
    views_count: int
    likes_count: int
    is_liked: bool | None = None
    podcast: PodcastResponse

class EpisodeCreate(BaseModel):
    title: StrippedString
    description: str
    episode_number: int

class ListEpisodes(BaseModel):
    quantity: int
    episodes: list[EpisodeResponse]


