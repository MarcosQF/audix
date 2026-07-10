from pydantic import BaseModel, ConfigDict, Field

from audix.podcasts.schemas import PodcastResponse
from audix.shared.types import StrippedString


class EpisodeResponse(BaseModel):
    id: int
    title: str
    description: str
    episode_number: int
    audio_url: str | None = None
    image_url: str | None = None
    duration: int
    views_count: int
    likes_count: int
    is_liked: bool | None = None
    podcast: PodcastResponse

class EpisodeCreate(BaseModel):
    title: StrippedString
    description: str
    duration: int
    episode_number: int

class ListEpisodes(BaseModel):
    quantity: int
    episodes: list[EpisodeResponse]


class EpisodeProgressUpdate(BaseModel):
    current_time_seconds: int = Field(
        ...,
        ge=0,
        description="O segundo exato em que o player de áudio do front-end se encontra atualmente.",
    )


class EpisodeProgressResponse(BaseModel):
    episode_id: int
    current_time_seconds: int
    last_position_seconds: int
    view_counted: bool
    duration: int | None = None

    model_config = ConfigDict(from_attributes=True)

class EpisodeAnalyticsResponse(BaseModel):
    episode_id: int
    total_views: int
    total_likes: int
    average_time_listened_seconds: float
    completion_rate_percentage: float


class AudioUploadUrlRequest(BaseModel):
    filename: str = Field(
        ...,
        description="Nome original do arquivo de áudio (ex: podcast_ep1.mp3)",
    )

class AudioUloadUrlResponse(BaseModel):
    upload_url: str
    object_name: str
