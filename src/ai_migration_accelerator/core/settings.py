from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # source_connection: str | None = None
    # target_connection: str | None = None

    # enable_llm_advisor: bool = False
    llm_model: str = "gemini-2.5-flash"
    google_api_key: str | None = None

    # include_sample_rows: bool = True
    # sample_row_limit: int = 3

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    hf_token: str | None = None
    hf_token_env_var: str = "HF_TOKEN"
    vector_dim: int = 384

    vector_table: str = "rag_documents"
    # run_containerized_migration: bool = False
    container_runtime: str = "podman"


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
