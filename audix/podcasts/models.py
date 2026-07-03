from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..shared.mixins.timestamp import TimestampMixin
from .enums import PodcastCategory

if TYPE_CHECKING:
    from audix.episodes.models import Episode
    from audix.users.models import User

class Podcast(Base, TimestampMixin):
    __tablename__ = "podcasts"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[PodcastCategory] = mapped_column(nullable=False)

    author: Mapped["User"] = relationship(
        "User",
        back_populates="podcasts",
        init=False,
        lazy="raise_on_sql"
    )

    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, default=None
    )

    episodes: Mapped[list["Episode"]] = relationship(
        "Episode", 
        back_populates="podcast", 
        cascade="all, delete-orphan",
        init=False
    )



