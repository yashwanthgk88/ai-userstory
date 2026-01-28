from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://securereq:securereq@db:5432/securereq"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    anthropic_api_key: str = ""
    encryption_key: str = "PzEY8tPkd2xkzBMNUYj7Owx9yw-kFhQZhcdyIaudsWY="
    cors_origins: str = "http://localhost:3000,http://localhost:80"
    port: int = 8000

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
