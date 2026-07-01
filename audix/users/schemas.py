from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from audix.shared.types import StrippedString
from audix.users.enums import UserRoles


class CreateUser(BaseModel):
    name: StrippedString = Field(max_length=50)
    email: EmailStr = Field(max_length=100)
    password: str = Field(min_length=8, max_length=50)


class ResponseUser(BaseModel):
    id: int
    name: StrippedString
    email: StrippedString
    created_at: datetime
    updated_at: datetime
    role: UserRoles


class ListUsers(BaseModel):
    quantity: int
    users: list[ResponseUser]


class UpdateUser(BaseModel):
    name: StrippedString | None = Field(default=None, max_length=50)
    email: EmailStr | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=50)


class UpdateUserRole(BaseModel):
    role: UserRoles
