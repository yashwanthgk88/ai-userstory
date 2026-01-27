from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://securereq:securereq@db:5432/securereq"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    anthropic_api_key: str = ""
    cors_origins: str = "http://localhost:3000,http://localhost:80"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
