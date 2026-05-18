from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),   # apps/api/.env OR project-root/.env
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Groq API
    groq_api_key: str = ""
    groq_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_text_model: str = "llama-3.3-70b-versatile"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "scene_contexts"

    # Agent
    router_confidence_threshold: float = 0.35
    max_keyframes: int = 8

    # Logging
    log_dir: str = "data/logs"


settings = Settings()
