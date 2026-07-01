from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audix.auth.hash import get_password_hash
from audix.database import SessionDep
from audix.shared.errors import NotFoundException
from audix.users.enums import UserRoles
from audix.users.errors import (
    EmailUniqueException,
    UserNotFoundByEmailException,
)

from .models import User
from .schemas import CreateUser, UpdateUser, UpdateUserRole


class UsersService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_data: CreateUser) -> User:
        db_user = User(
            name=user_data.name,
            email=user_data.email,
            password=get_password_hash(user_data.password),
            role=UserRoles.USER,
        )

        self.session.add(db_user)

        try:
            await self.session.commit()
        except Exception:
            raise EmailUniqueException()

        await self.session.refresh(db_user)
        return db_user

    async def get_by_id(self, user_id: int) -> User:
        query = select(User).where(User.id == user_id) 
        user_db = await self.session.scalar(query)

        if not user_db:
            raise NotFoundException(item='Usuário', item_id=user_id)

        return user_db

    async def get_by_email(self, email: str) -> User:
        query = select(User).where(User.email == email) 
        user_db = await self.session.scalar(query)

        if not user_db:
            raise UserNotFoundByEmailException(user_email=email)

        return user_db

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        query = select(User).offset(skip).limit(limit)
        users = await self.session.scalars(query)
        return list(users)

    async def update(self, user_id: int, user_data: UpdateUser) -> User:
        user = await self.get_by_id(user_id)

        update_dict = user_data.model_dump(exclude_unset=True)

        if 'password' in update_dict:
            update_dict['password'] = get_password_hash(
                update_dict['password']
            )

        for key, value in update_dict.items():
            setattr(user, key, value)

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_role(self,user_id: int, role_dict: UpdateUserRole) -> User:
        user = await self.get_by_id(user_id)

        user.role = role_dict.role

        await self.session.commit()
        await self.session.refresh(user)

        return user

    async def delete(self, user_id: int) -> bool:
        user = await self.get_by_id(user_id)

        await self.session.delete(user)
        await self.session.commit()
        return True

async def get_user_service(session: SessionDep):
    return UsersService(session=session)

UserServiceDep = Annotated[UsersService, Depends(get_user_service)]
