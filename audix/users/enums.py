import enum


class UserRoles(str, enum.Enum):
    USER = 'user'
    ADMIN = 'admin'
