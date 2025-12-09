"""
Embedding model configuration for Korean text processing
"""
from langchain_community.embeddings import HuggingFaceEmbeddings
from config import settings
from loguru import logger


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Initialize Korean-optimized embedding model

    Returns:
        HuggingFaceEmbeddings: Configured embedding model
    """
    logger.info(f"Initializing embedding model: {settings.EMBEDDING_MODEL_NAME}")

    embeddings = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL_NAME,
        model_kwargs={"device": settings.EMBEDDING_DEVICE},
        encode_kwargs={
            "normalize_embeddings": True,  # Cosine similarity optimization
            "batch_size": 32
        }
    )

    logger.info("Embedding model initialized successfully")
    return embeddings


def get_embedding_dimension() -> int:
    """
    Get the dimension of the embedding model

    Returns:
        int: Embedding vector dimension
    """
    return settings.QDRANT_VECTOR_SIZE
