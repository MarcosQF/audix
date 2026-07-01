from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from audix.users.enums import UserRoles

from ..database import Base
from ..shared.mixins.timestamp import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    
    name: Mapped[str] = mapped_column(str(50))
    email: Mapped[str] = mapped_column(str(100), unique=True)
    password: Mapped[str] = mapped_column(str(255))
    role: Mapped[UserRoles] = mapped_column(default=UserRoles.USER)
