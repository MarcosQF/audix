from http import HTTPStatus

from fastapi import APIRouter

from audix.shared.permissions import RequireAdmin, RequireUser
from audix.users.schemas import (
    CreateUser,
    ListUsers,
    ResponseUser,
    UpdateUser,
    UpdateUserRole,
)
from audix.users.service import UserServiceDep

router = APIRouter(prefix='/users', tags=['Users'])

@router.get('/me', response_model=ResponseUser, status_code=HTTPStatus.OK)
async def get_current_user(user: RequireUser):
    return user

@router.post("/", response_model=ResponseUser, status_code=HTTPStatus.CREATED)
async def create_user(user_data: CreateUser, service: UserServiceDep):
    return await service.create(user_data)

@router.get("/", response_model=ListUsers, status_code=HTTPStatus.OK)
async def list_users(
    user: RequireAdmin,
    service: UserServiceDep,
    skip: int = 0,
    limit: int = 100,
):
    users = await service.list_all(skip=skip, limit=limit) 
    return {"quantity": len(users), "users": users} 

@router.get(
    "/{user_id}",
    response_model=ResponseUser,
    status_code=HTTPStatus.OK
)
async def get_user_by_id(
    user: RequireAdmin,
    user_id: int,
    service: UserServiceDep,
):
    return await service.get_by_id(user_id)

@router.get(
    "/email/{email}",
    response_model=ResponseUser,
    status_code=HTTPStatus.OK
)
async def get_user_by_email(
    user: RequireAdmin,
    email: str,
    service: UserServiceDep,
):
    return await service.get_by_email(email)

@router.patch(
    "/{user_id}",
    response_model=ResponseUser,
    status_code=HTTPStatus.OK
)
async def update_user(
    user: RequireUser,
    user_id: int,
    user_data: UpdateUser,
    service: UserServiceDep,
):
    return await service.update(user_id, user_data)

@router.delete("/{user_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_user(
    user: RequireAdmin,
    user_id: int,
    service: UserServiceDep,
):
    await service.delete(user_id)
    return None


@router.patch(
    "/{user_id}/role",
    response_model=ResponseUser,
    status_code=HTTPStatus.OK
)
async def update_user_role(
    user: RequireAdmin,
    user_id: int,
    user_data: UpdateUserRole,
    service: UserServiceDep,
):
    return await service.update_role(user_id, user_data)
