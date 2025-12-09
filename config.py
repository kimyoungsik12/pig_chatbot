"""
Configuration management for Pig Farming RAG LLM System
Environment-driven: values are loaded from .env
"""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # vLLM Server Configuration
    VLLM_BASE_URL: str = Field(..., env="VLLM_BASE_URL")
    VLLM_MODEL_NAME: str = Field(..., env="VLLM_MODEL_NAME")
    VLLM_API_KEY: str = Field("EMPTY", env="VLLM_API_KEY")  # vLLM doesn't require API key
    VLLM_TEMPERATURE: float = Field(..., env="VLLM_TEMPERATURE")
    VLLM_MAX_TOKENS: int = Field(..., env="VLLM_MAX_TOKENS")

    # Qdrant Vector Store Configuration
    QDRANT_HOST: str = Field(..., env="QDRANT_HOST")
    QDRANT_PORT: int = Field(..., env="QDRANT_PORT")
    QDRANT_COLLECTION_NAME: str = Field(..., env="QDRANT_COLLECTION_NAME")
    QDRANT_VECTOR_SIZE: int = Field(..., env="QDRANT_VECTOR_SIZE")

    # Embedding Model Configuration
    EMBEDDING_MODEL_NAME: str = Field(..., env="EMBEDDING_MODEL_NAME")
    EMBEDDING_DEVICE: str = Field(..., env="EMBEDDING_DEVICE")  # cpu/cuda

    # Text Processing Configuration
    CHUNK_SIZE: int = Field(..., env="CHUNK_SIZE")
    CHUNK_OVERLAP: int = Field(..., env="CHUNK_OVERLAP")

    # RAG Configuration
    RETRIEVAL_TOP_K: int = Field(..., env="RETRIEVAL_TOP_K")
    RETRIEVAL_SCORE_THRESHOLD: float = Field(..., env="RETRIEVAL_SCORE_THRESHOLD")

    # API Server Configuration
    API_HOST: str = Field(..., env="API_HOST")
    API_PORT: int = Field(..., env="API_PORT")
    API_TITLE: str = Field("Pig Farming RAG LLM API", env="API_TITLE")
    API_VERSION: str = Field("1.0.0", env="API_VERSION")

    # Crawler Configuration
    CRAWLER_SCHEDULE_TIME: str = Field(..., env="CRAWLER_SCHEDULE_TIME")  # Daily at 3 AM
    CRAWLER_USER_AGENT: str = Field(..., env="CRAWLER_USER_AGENT")
    CRAWLER_TIMEOUT: int = Field(..., env="CRAWLER_TIMEOUT")
    CRAWLER_MAX_RETRIES: int = Field(..., env="CRAWLER_MAX_RETRIES")

    # Logging Configuration
    LOG_LEVEL: str = Field(..., env="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(None, env="LOG_FILE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
