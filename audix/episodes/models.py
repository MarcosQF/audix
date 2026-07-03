from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from audix.database import Base

from ..shared.mixins.timestamp import TimestampMixin

if TYPE_CHECKING:
    from audix.podcasts.models import Podcast

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
