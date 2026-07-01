from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audix.shared.errors import UnauthorizedException

from ..database import get_session
from ..users.models import User
from .hash import verify_password
from .token import create_access_token


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def login_for_jwt(self, form_data: OAuth2PasswordRequestForm):
        query = select(User).where(User.email == form_data.username)

        user = await self.session.scalar(query)

        if not user or not verify_password(form_data.password, user.password):
            raise UnauthorizedException(detail='Incorrect email or password')

        access_token = create_access_token({'sub': form_data.username})

        return access_token


def get_auth_service(session=Depends(get_session)):
    return AuthService(session=session)


T_AuthService = Annotated[AuthService, Depends(get_auth_service)]
