"""Runtime settings, read from environment / .env (server-side only)."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    # .env is looked up next to the api/ folder and in it, whatever the working directory is
    model_config = SettingsConfigDict(
        env_file=(API_DIR.parent / ".env", API_DIR / ".env"), extra="ignore"
    )

    firms_map_key: str = ""
    data_dir: Path = API_DIR / "data"
    # one origin, or several separated by commas (production and preview deployments)
    web_origin: str = "http://localhost:3000"

    @property
    def web_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.web_origin.split(",") if o.strip()]

    @field_validator("data_dir")
    @classmethod
    def _relative_to_api(cls, v: Path) -> Path:
        """A relative DATA_DIR (like ./data in .env) means relative to api/, not to the cwd."""
        return v if v.is_absolute() else (API_DIR / v).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
