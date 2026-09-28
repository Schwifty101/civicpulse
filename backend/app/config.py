from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres
    postgres_user: str = "civicpulse"
    postgres_password: str = "civicpulse"
    postgres_db: str = "civicpulse"
    postgres_host: str = "database"
    postgres_port: int = 5432

    # Redis
    redis_host: str = "cache"
    redis_port: int = 6379

    # Backend behaviour
    triage_provider: str = "rules"  # rules | simulated | llm | ollama
    log_level: str = "INFO"
    rate_limit_per_minute: int = 20
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    # Groq (OpenAI-compatible)
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.1-8b-instant"

    # Ollama
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:1b"

    # Testing / CI override — takes priority over postgres_* fields when set
    database_url_override: str = ""

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
