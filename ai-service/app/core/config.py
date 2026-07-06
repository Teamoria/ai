"""Application configuration."""

from pathlib import Path
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


AI_SERVICE_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=AI_SERVICE_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Teamoria AI Service"
    database_url: str = ""
    db_connection: str = ""
    db_host: str = ""
    db_port: str = ""
    db_database: str = ""
    db_username: str = ""
    db_password: str = ""
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
    openai_model: str = "gpt-4o-mini"
    pinecone_api_key: str = ""
    pinecone_index: str = ""
    pinecone_index_name: str = ""
    pinecone_host: str = ""
    pinecone_namespace: str = ""
    pinecone_namespace_prefix: str = "teamoria"
    embedding_dimensions: int = 1024

    @model_validator(mode="after")
    def normalize_database_settings(self) -> "Settings":
        self.database_url = self._resolved_database_url()
        return self

    def _resolved_database_url(self) -> str:
        database_url = self.database_url.strip()

        if database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql+psycopg2://", 1)

        if database_url:
            return database_url

        db_connection = self.db_connection.strip().lower()
        if db_connection in {"mysql", "mariadb"} and self.db_host and self.db_database:
            port = self.db_port or "3306"
            username = quote_plus(self.db_username)
            password = quote_plus(self.db_password)
            database = quote_plus(self.db_database)
            return f"mysql+pymysql://{username}:{password}@{self.db_host}:{port}/{database}?charset=utf8mb4"

        if db_connection in {"pgsql", "postgres", "postgresql"} and self.db_host and self.db_database:
            port = self.db_port or "5432"
            username = quote_plus(self.db_username)
            password = quote_plus(self.db_password)
            database = quote_plus(self.db_database)
            return f"postgresql+psycopg2://{username}:{password}@{self.db_host}:{port}/{database}"

        return "postgresql+psycopg://postgres:postgres@localhost:5432/teamoria_ai"


settings = Settings()
