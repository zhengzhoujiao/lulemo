from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # 应用基础配置
    APP_NAME: str = "噜了么 API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # MongoDB 配置
    MONGODB_URL: str = "mongodb://localhost:27020"
    MONGODB_DB: str = "lulemo"

    # JWT 配置
    SECRET_KEY: str = Field(min_length=32, repr=False)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 天

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        hide_input_in_errors=True,
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if value.lower().startswith(("change", "replace", "your-")) or len(set(value)) == 1:
            raise ValueError("SECRET_KEY must be a randomly generated secret, not a placeholder")
        return value


@lru_cache()
def get_settings() -> Settings:
    return Settings()
