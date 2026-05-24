from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    version: str = "0.1.0"
    database_url: str = "postgresql+asyncpg://fuzhify:fuzhify@postgres:5432/fuzhify"

    model_config = {"env_file": ".env"}


settings = Settings()
