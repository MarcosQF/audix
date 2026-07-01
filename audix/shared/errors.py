from http import HTTPStatus

from fastapi import HTTPException


class ApiException(HTTPException):
    def __init__(self, status_code: int, detail: str, error_code: str):
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers={'X-Error-Code': error_code},
        )


class NotFoundException(ApiException):
    def __init__(self, item, item_id):
        super().__init__(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f'{item} com id {item_id} não econtrado',
            error_code='NOT_FOUND',
        )


class UnauthorizedException(ApiException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail=detail,
            error_code='UNAUTHORIZED',
        )


class ForbbiddenException(ApiException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=HTTPStatus.FORBIDDEN,
            detail=detail,
            error_code='FORBIDDEN',
        )
