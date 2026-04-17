from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    
    # Elasticsearch
    es_host : str = Field(default="localhost", description="Elasticsearch host")
    es_port : int = Field(default=9200, description="Elasticsearch port")
    es_index: str = Field(default="plagiarism_documents", description="Index name")
    es_user: str = Field(default="elastic", description="ES username")
    es_password: str = Field(default="changeme", description="ES password")
    es_scheme: str = Field(default="http", description="HTTP or HTTPS")
    
    # Ollama
    ollama_host: str = Field(
        default="http://localhost:11434", description="Ollama API URL"
    )
    ollama_embed_model: str = Field(
        default="nomic-embed-text", description="Embedding model"
    )
    ollama_chat_model: str = Field(
        default="llama3.2", description="Chat model for analysis"
    )
    ollama_timeout: int = Field(default=60, description="Request timeout in seconds")


@lru_cache()
def get_settings() -> Settings:
    return Settings()