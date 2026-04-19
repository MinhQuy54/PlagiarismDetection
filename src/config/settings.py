"""Configuration settings for Plagiarism Detection Service."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Elasticsearch
    es_host: str = Field(default="localhost", description="Elasticsearch host")
    es_port: int = Field(default=9200, description="Elasticsearch port")
    es_index: str = Field(default="plagiarism_documents", description="Index name")
    es_user: str = Field(default="elastic", description="ES username")
    es_password: str = Field(default="changeme", description="ES password")
    es_scheme: str = Field(default="http", description="HTTP or HTTPS")

    # Analyzer mode: 'external' (Gemini) or 'internal' (Ollama)
    analyzer_mode: str = Field(
        default="internal", description="Analyzer mode: 'external' (Gemini) or 'internal' (Ollama)"
    )

    # Ollama (internal mode)
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

    # Gemini (external mode)
    gemini_api_key: str = Field(
        default="", description="Gemini API key"
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash", description="Gemini model name"
    )
    gemini_timeout: int = Field(default=60, description="Gemini request timeout")
    gemini_api_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/models",
        description="Gemini API base URL"
    )

    # gRPC Server
    grpc_host: str = Field(default="0.0.0.0", description="gRPC bind host")
    grpc_port: int = Field(default=50051, description="gRPC port")
    grpc_max_workers: int = Field(default=3, description="Thread pool size")

    # TLS Settings
    grpc_tls_enabled: bool = Field(default=False, description="Enable TLS for gRPC")
    grpc_cert_path: str = Field(default="certs/plagiarism-server.crt", description="Server certificate path")
    grpc_key_path: str = Field(default="certs/plagiarism-server.key", description="Server private key path")
    grpc_ca_path: str = Field(default="certs/ca.crt", description="CA certificate path")
    grpc_require_client_cert: bool = Field(default=False, description="Require client certificate (mTLS)")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_dir: str = Field(default="logs", description="Log directory for JSON logs")
    service_name: str = Field(default="plagiarism", description="Service name for logging")
    metrics_port: int = Field(default=9107, description="Prometheus metrics port")

    # Plagiarism Thresholds
    similarity_critical: float = Field(
        default=0.95, description="Critical plagiarism threshold"
    )
    similarity_high: float = Field(default=0.85, description="High plagiarism threshold")
    similarity_medium: float = Field(
        default=0.70, description="Medium plagiarism threshold"
    )
    similarity_low: float = Field(default=0.50, description="Low plagiarism threshold")

    # Text Chunking
    chunk_size: int = Field(default=100, description="Words per chunk")
    chunk_overlap: int = Field(default=20, description="Overlap between chunks")
    min_chunk_size: int = Field(default=30, description="Minimum chunk size")
    min_content_length: int = Field(default=200, description="Minimum content length in chars to index")

    # Search
    top_k_results: int = Field(default=10, description="Max search results")
    min_score_threshold: float = Field(
        default=0.50, description="Minimum similarity score"
    )
    max_results_per_source: int = Field(
        default=3, description="Max matches from one source"
    )

    # Embedding
    embedding_dims: int = Field(default=768, description="Embedding dimensions")
    embedding_batch_size: int = Field(default=32, description="Batch size for embedding")

    # MinIO Storage
    minio_endpoint: str = Field(default="127.0.0.1", description="MinIO server endpoint")
    minio_port: int = Field(default=10005, description="MinIO server port")
    minio_access_key: str = Field(default="", description="MinIO access key")
    minio_secret_key: str = Field(default="", description="MinIO secret key")
    minio_use_ssl: bool = Field(default=False, description="Use SSL for MinIO connection")
    minio_bucket_name: str = Field(default="lvtn", description="Default MinIO bucket name")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def es_url(self) -> str:
        """Get Elasticsearch URL."""
        return f"{self.es_scheme}://{self.es_host}:{self.es_port}"

    @property
    def minio_url(self) -> str:
        """Get MinIO endpoint with port."""
        return f"{self.minio_endpoint}:{self.minio_port}"

    def get_severity(self, similarity: float) -> str:
        """Get severity level from similarity score."""
        if similarity >= self.similarity_critical:
            return "CRITICAL"
        elif similarity >= self.similarity_high:
            return "HIGH"
        elif similarity >= self.similarity_medium:
            return "MEDIUM"
        elif similarity >= self.similarity_low:
            return "LOW"
        return "SAFE"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
