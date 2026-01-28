from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://securereq:securereq@db:5432/securereq"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    # LLM provider settings
    llm_provider: str = "anthropic"  # anthropic | openai | azure_openai | gemini | openai_compatible
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    gemini_api_key: str = ""
    openai_compatible_url: str = ""
    openai_compatible_api_key: str = ""
    default_model: str = ""  # if empty, uses provider default
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
