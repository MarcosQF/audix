from pydantic import BaseModel, ConfigDict, computed_field

from audix.episodes.schemas import (
    EpisodeResponse,
)


class ListPlaylists(BaseModel):
    quantity: int
    playlists: list[PlaylistResponse]

    model_config = ConfigDict(from_attributes=True)

class PlaylistCreate(BaseModel):
    name: str
    description: str | None = None

class PlaylistResponse(BaseModel):
    id: int
    name: str
    description: str | None
    user_id: int
    episodes: list[EpisodeResponse] = []

    @computed_field
    def episodes_quantity(self) -> int:
        return len(self.episodes)

    model_config = ConfigDict(from_attributes=True)
