from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column


class TimestampMixin(MappedAsDataclass):
    created_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(),
        default=None,
        init=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(),
        onupdate=func.now(),
        default=None,
        init=False
    )
