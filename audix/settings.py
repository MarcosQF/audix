from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8',
    )

    DATABASE_URL: str = 'postgresql+asyncpg://db_user:password@postgres:5432/db_app'
    # DATABASE_URL: str = 'postgresql+asyncpg://db_user:password@localhost:5432/db_app'
    JWT_SECRET_KEY: str = 'SECRET_KEY'
    JWT_ALGORITHM: str = 'HS256'
    ADMIN_NAME: str = 'Admin'
    ADMIN_EMAIL: str = 'admin@email.com'
    ADMIN_PASSWORD: str = 'minhasenha'
    MINIO_ENDPOINT: str = 'http://minio:9000'
    MINIO_ACCESS_KEY: str = 'minioadmin'
    MINIO_SECRET_KEY: str = 'minioadmin'
 
settings = Settings() # type: ignore
