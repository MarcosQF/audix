from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, decode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audix.shared.errors import ForbbiddenException, UnauthorizedException
from audix.users.enums import UserRoles
from audix.users.models import User

from ..database import get_session
from ..settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/auth/token')


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    token: str = Depends(oauth2_scheme),
):
    try:
        payload = decode(
            token, settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM
        )
    except DecodeError:
        raise UnauthorizedException(
            detail='Não foi possivel validar as credenciais'
        )

    sub_email = payload.get('sub')

    if not sub_email:
        raise UnauthorizedException(
            detail='Não foi possivel validar as credenciais'
        )

    user = await session.scalar(select(User).where(User.email == sub_email))

    if not user:
        raise UnauthorizedException(detail='Email ou senha incorretos')

    return user


class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise ForbbiddenException(detail='Operação proibida')
        return current_user


RequireUser = Annotated[
    User, Depends(RoleChecker([UserRoles.USER, UserRoles.ADMIN]))
]

RequireAdmin = Annotated[User, Depends(RoleChecker([UserRoles.ADMIN]))]
