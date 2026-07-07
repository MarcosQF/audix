from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from audix.database import Base

from ..shared.mixins.timestamp import TimestampMixin

if TYPE_CHECKING:
    from audix.podcasts.models import Podcast
    from audix.users.models import User

episode_likes_association = Table(
    "episode_likes",
    Base.metadata,
    Column("user_id", ForeignKey(
        "users.id",
        ondelete="CASCADE"
    ), primary_key=True),
    Column(
        "episode_id",
        ForeignKey("episodes.id", ondelete="CASCADE"),
        primary_key=True
    ),
)


class Episode(Base, TimestampMixin):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    audio_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
        init=False
    )
    
    podcast_id: Mapped[int] = mapped_column(
            ForeignKey("podcasts.id", ondelete="CASCADE")
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, default=None
    )

    duration: Mapped[int] = mapped_column(Integer, nullable=True, init=False)


    podcast: Mapped["Podcast"] = relationship(
        "Podcast",
        back_populates="episodes",
        init=False
    )

    views_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    likes_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )

    liked_by_users: Mapped[list["User"]] = relationship(
        "User",
        secondary=episode_likes_association,
        lazy="raise_on_sql",
        init=False
    )

    @property
    def is_liked(self) -> bool | None:
        return getattr(self, "_is_liked", None)

    @is_liked.setter
    def is_liked(self, value: bool):
        self._is_liked = value

