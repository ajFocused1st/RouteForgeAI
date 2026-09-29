from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    app_name: str = "RouteForge AI"
    app_version: str = "0.1.0"
    environment: str = "local"
    debug: bool = False
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./routeforge.db"
    valhalla_url: str = "http://127.0.0.1:8002"
    valhalla_costing: str = "auto"
    valhalla_osm_region: str = "florida"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_ai_model: str = "llama3.1"
    ollama_vision_model: str = "llama3.2-vision"
    geocoder_url: str = "https://nominatim.openstreetmap.org"
    map_data_path: str = "map-data"
    routing_data_path: str = "routing-data"
    max_vision_image_bytes: int = 8 * 1024 * 1024
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ROUTEFORGE_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
