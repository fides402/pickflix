import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "openai/gpt-oss-120b:free"
    plugin_scan_paths: str = "/usr/lib/vst3,~/.vst3"
    free_models_cache_ttl_seconds: int = 3600
    jobs_data_dir: str = "jobs_data"

    def plugin_scan_path_list(self) -> list[str]:
        return [os.path.expanduser(p.strip()) for p in self.plugin_scan_paths.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
