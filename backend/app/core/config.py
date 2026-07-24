from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Accept postgres:// / postgresql:// and prefer asyncpg + ssl for Neon."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    if "+asyncpg" not in url:
        return url

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    # Neon / most hosts: asyncpg wants ssl=require (not sslmode=)
    if "sslmode" in query:
        query.setdefault("ssl", query.pop("sslmode"))
    if "ssl" not in query and "neon.tech" in (parsed.hostname or ""):
        query["ssl"] = "require"
    return urlunparse(parsed._replace(query=urlencode(query)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TasksDAV"
    base_url: str = "http://127.0.0.1:8000"
    secret_key: str = "dev-change-me"
    database_url: str = "sqlite+aiosqlite:///./tasksdav.db"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_path: str = "/auth/google/callback"

    session_cookie: str = "tasksdav_session"
    session_max_age: int = 60 * 60 * 24 * 30

    @property
    def google_redirect_uri(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.google_redirect_path}"

    @property
    def async_database_url(self) -> str:
        return normalize_database_url(self.database_url)

    @property
    def session_https_only(self) -> bool:
        return self.base_url.lower().startswith("https://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
