from http import HTTPStatus

from audix.shared.errors import ApiException


class UserNotFoundByEmailException(ApiException):
    def __init__(self, user_email: str):
        super().__init__(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f'Usuário com email {user_email} não econtrado',
            error_code='NOT_FOUND',
        )

class EmailUniqueException(ApiException):
    def __init__(self):
        super().__init__(
            status_code=HTTPStatus.CONFLICT,
            detail="Email ja cadastrado para outro usuario",
            error_code="CONFLICT"
        )
