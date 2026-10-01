"""Application configuration loaded from environment variables / .env.

Uses a tiny stdlib loader (no pydantic-settings) to keep dependencies minimal
and avoid build friction on newer Python versions.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


@dataclass
class Settings:
    openai_api_key: str | None = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY") or None
    )
    openai_chat_model: str = field(
        default_factory=lambda: os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    )
    openai_embed_model: str = field(
        default_factory=lambda: os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    )
    database_path: str = field(
        default_factory=lambda: os.environ.get("DATABASE_PATH", str(BASE_DIR / "jobhunter.db"))
    )

    # Adzuna job source (optional): https://developer.adzuna.com/
    adzuna_app_id: str | None = field(
        default_factory=lambda: os.environ.get("ADZUNA_APP_ID") or None
    )
    adzuna_app_key: str | None = field(
        default_factory=lambda: os.environ.get("ADZUNA_APP_KEY") or None
    )
    adzuna_country: str = field(
        default_factory=lambda: os.environ.get("ADZUNA_COUNTRY", "gb")
    )
    adzuna_query: str = field(
        default_factory=lambda: os.environ.get("ADZUNA_QUERY", "software engineer")
    )

    # JSearch aggregator via RapidAPI (optional): aggregates LinkedIn, Indeed,
    # Glassdoor, ZipRecruiter and more. https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
    rapidapi_key: str | None = field(
        default_factory=lambda: os.environ.get("RAPIDAPI_KEY") or None
    )
    jsearch_host: str = field(
        default_factory=lambda: os.environ.get("JSEARCH_HOST", "jsearch.p.rapidapi.com")
    )

    # Default role/location used for aggregated queries and deep-link searches.
    job_query: str = field(
        default_factory=lambda: os.environ.get("JOB_QUERY", "software engineer")
    )
    job_location: str = field(
        default_factory=lambda: os.environ.get("JOB_LOCATION", "remote")
    )

    # Gmail status auto-updates (optional): OAuth client secret + token paths.
    gmail_credentials_path: str = field(
        default_factory=lambda: os.environ.get(
            "GMAIL_CREDENTIALS_PATH", str(BASE_DIR / "credentials.json")
        )
    )
    gmail_token_path: str = field(
        default_factory=lambda: os.environ.get("GMAIL_TOKEN_PATH", str(BASE_DIR / "token.json"))
    )

    # Auto-search: public ATS boards as "<greenhouse|lever|ashby>:<slug>", comma-separated.
    ats_boards: list[str] = field(
        default_factory=lambda: [
            s.strip() for s in os.environ.get("ATS_BOARDS", "").split(",") if s.strip()
        ]
    )

    # Auto-apply: details not present in the parsed CV.
    resume_path: str | None = field(default_factory=lambda: os.environ.get("RESUME_PATH") or None)
    applicant_location: str = field(default_factory=lambda: os.environ.get("APPLICANT_LOCATION", ""))
    applicant_linkedin: str = field(default_factory=lambda: os.environ.get("APPLICANT_LINKEDIN", ""))
    applicant_github: str = field(default_factory=lambda: os.environ.get("APPLICANT_GITHUB", ""))
    applicant_portfolio: str = field(default_factory=lambda: os.environ.get("APPLICANT_PORTFOLIO", ""))
    # Headed (False) opens a visible browser on the backend host for review; use True in Docker.
    autoapply_headless: bool = field(
        default_factory=lambda: os.environ.get("AUTOAPPLY_HEADLESS", "false").lower() in ("1", "true", "yes")
    )

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def adzuna_enabled(self) -> bool:
        return bool(self.adzuna_app_id and self.adzuna_app_key)

    @property
    def jsearch_enabled(self) -> bool:
        return bool(self.rapidapi_key)

    @property
    def gmail_enabled(self) -> bool:
        # Enabled if a token or credentials file exists to attempt a connection.
        return os.path.exists(self.gmail_token_path) or os.path.exists(
            self.gmail_credentials_path
        )


settings = Settings()
