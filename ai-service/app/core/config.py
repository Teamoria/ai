"""Application configuration."""

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Teamoria AI Service"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/teamoria_ai"
    internal_api_key: str = "change_me"
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_llm_model: str = "llama-3.3-70b-versatile"
    groq_transcription_model: str = "whisper-large-v3-turbo"
    groq_verify_ssl: bool = True
    groq_request_timeout: float = 90.0
    ffmpeg_path: str = "ffmpeg"
    media_chunk_seconds: int = 300
    upload_temp_dir: str = "tmp/uploads"
    openai_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index: str = ""
    pinecone_index_name: str = ""
    pinecone_host: str = ""
    pinecone_namespace: str = ""
    pinecone_namespace_prefix: str = "teamoria"
    embedding_dimensions: int = 1024


settings = Settings()
