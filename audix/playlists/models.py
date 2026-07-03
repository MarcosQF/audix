from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from audix.database import Base
from audix.shared.mixins.timestamp import TimestampMixin

if TYPE_CHECKING:
    from audix.episodes.models import Episode
    from audix.users.models import User

playlist_episode_association = Table(
    "playlist_episodes",
    Base.metadata,
    Column(
        "playlist_id",
        ForeignKey("playlists.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "episode_id",
        ForeignKey("episodes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Playlist(Base, TimestampMixin):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["User"] = relationship("User", init=False, lazy="raise_on_sql")

    episodes: Mapped[list["Episode"]] = relationship(
        "Episode",
        secondary=playlist_episode_association,
        backref="playlists",
        init=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
