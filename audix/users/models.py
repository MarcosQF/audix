from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from audix.users.enums import UserRoles

from ..database import Base
from ..shared.mixins.timestamp import TimestampMixin

if TYPE_CHECKING:
    from audix.podcasts.models import Podcast

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(255))

    podcasts: Mapped[list["Podcast"]] = relationship(
        "Podcast",
        back_populates="author",
        init=False
    )

    role: Mapped[UserRoles] = mapped_column(default=UserRoles.USER)

