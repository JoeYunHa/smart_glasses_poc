from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),   # apps/api/.env OR project-root/.env
        env_file_encoding="utf-8-sig",
        case_sensitive=False,
    )

    # OpenAI API
    openai_api_key: str = ""
    openai_vision_model: str = "gpt-4o"
    openai_text_model: str = "gpt-4o-mini"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "scene_contexts"

    # Agent
    router_confidence_threshold: float = 0.40
    max_keyframes: int = 8

    # Logging
    log_dir: str = "data/logs"


settings = Settings()
