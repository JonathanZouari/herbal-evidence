from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    log_level: str = "INFO"
    supabase_url: str
    supabase_secret_key: SecretStr | None = None
    database_url: str
    cors_allowed_origins: str = ""
    # quotas (D-018)
    max_requests_per_day: int = 5
    max_open_requests: int = 3
    ip_requests_per_minute: int = 120
    # research worker (D-010, D-019): off unless explicitly enabled; tests never start it
    worker_enabled: bool = False
    worker_poll_seconds: float = 5
    worker_lease_seconds: int = 120
    # AI provider (D-008): anything missing -> NullProvider -> structured "ai_not_configured" failure
    ai_provider: Literal["openai", "none"] = "none"
    ai_model: str = ""
    ai_api_key: SecretStr | None = None
    ai_timeout_seconds: float = 180   # a strong model on ~20 abstracts takes ~80s
    # literature (D-009)
    ncbi_api_key: SecretStr | None = None
    ncbi_tool: str = "herbal-evidence"
    ncbi_email: str = ""
    literature_max_results: int = 20
    # herb reference photo (Wikimedia; no key needed, but their API etiquette asks for a contact address)
    wikimedia_contact_email: str = ""

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.jwt_issuer}/.well-known/jwks.json"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
