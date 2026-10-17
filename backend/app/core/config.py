"""Application configuration settings."""
from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = Field(
        default="sqlite:///./orbit_lab.db",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
    )

    # Auth
    auth_enabled: bool = Field(default=False)

    # LLM (optional, for advisory explanations)
    llm_api_key: str | None = Field(default=None)
    llm_provider: str | None = Field(default=None)
    llm_model: str | None = Field(default=None)
    llm_base_url: str | None = Field(default=None)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()