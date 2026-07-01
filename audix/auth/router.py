from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from audix.auth.service import T_AuthService

from .schemas import Token

router = APIRouter(prefix='/auth', tags=['Auth'])


@router.post('/token', response_model=Token)
async def login_for_access_token(
    service: T_AuthService,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    access_token = await service.login_for_jwt(form_data=form_data)

    return {'access_token': access_token, 'token_type': 'bearer'}
