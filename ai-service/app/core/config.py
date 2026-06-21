"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Teamoria AI Service"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/teamoria_ai"
    internal_api_key: str = "change_me"
    openai_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index_name: str = ""


settings = Settings()
