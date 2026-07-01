from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from jwt import encode

from ..settings import settings


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(ZoneInfo('America/Sao_Paulo')) + timedelta(
        hours=3
    )

    to_encode.update({'exp': expire})

    encoded_jwt = encode(
        payload=to_encode,
        key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt
