from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audix.auth.hash import get_password_hash
from audix.users.models import User
from audix.users.schemas import UserRoles

from .settings import settings


async def create_initial_admin(session: AsyncSession):
    stmt = select(User).where(User.id == 1)
    db_user = await session.scalar(stmt)

    if not db_user:
        db_user = User(
            name=settings.ADMIN_NAME,
            email=settings.ADMIN_EMAIL,
            password=get_password_hash(settings.ADMIN_PASSWORD),
            role=UserRoles.ADMIN
        )

        session.add(db_user)
        await session.commit()
