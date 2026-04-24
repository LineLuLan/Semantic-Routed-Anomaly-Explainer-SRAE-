"""Central configuration loader for SRAE.

Reads values from a `.env` file (if present) and environment variables.
Every other module should import `settings` from here rather than calling
`os.getenv` directly so that defaults and validation live in one place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH, override=False)


@dataclass(frozen=True)
class Settings:
    postgres_url: str
    groq_api_key: str
    groq_model: str
    embedding_model: str
    log_level: str

    @property
    def has_groq_key(self) -> bool:
        return bool(self.groq_api_key) and self.groq_api_key != "your_groq_api_key_here"


def _require(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(
            f"Missing required environment variable `{name}`. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


def load_settings() -> Settings:
    return Settings(
        postgres_url=_require(
            "POSTGRES_URL",
            "postgresql+psycopg2://postgres:postgres@localhost:5432/srae",
        ),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_model=os.getenv("GROQ_MODEL", "llama3-8b-8192"),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


settings = load_settings()
