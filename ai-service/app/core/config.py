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
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174"
    )
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
    groq_transcription_language: str = ""
    groq_transcription_prompt: str = (
        "The audio may contain Arabic, English, or mixed Arabic-English project-management discussion. "
        "Transcribe names, product names, API terms, numbers, and technical terms clearly. "
        "Do not translate; preserve the spoken language. Ignore subtitles, background music, repeated filler, "
        "and unrelated captions when they are not spoken by the main speaker."
    )
    groq_verify_ssl: bool = True
    groq_request_timeout: float = 90.0
    ffmpeg_path: str = "ffmpeg"
    media_chunk_seconds: int = 300
    upload_temp_dir: str = "tmp/uploads"
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    tesseract_tessdata_dir: str = str(AI_SERVICE_ROOT / "tessdata")
    backend_file_api_key: str = ""
    backend_file_api_key_header: str = "x-api-key"
    backend_file_bearer_token: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o-mini"
    pinecone_api_key: str = ""
    pinecone_index: str = ""
    pinecone_index_name: str = ""
    pinecone_host: str = ""
    pinecone_namespace: str = ""
    pinecone_namespace_prefix: str = "teamoria"
    embedding_provider: str = "local"
    embedding_model: str = "text-embedding-3-small"
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

    def resolved_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
