"""
Basic tests for system components
"""
import pytest
from config import settings


def test_config_loaded():
    """Test that configuration is loaded correctly"""
    assert settings.VLLM_BASE_URL is not None
    assert settings.QDRANT_HOST is not None
    assert settings.QDRANT_PORT > 0


def test_embedding_model_name():
    """Test that embedding model name is valid"""
    assert "ko" in settings.EMBEDDING_MODEL_NAME.lower()


def test_chunk_settings():
    """Test that chunking settings are reasonable"""
    assert settings.CHUNK_SIZE > 0
    assert settings.CHUNK_OVERLAP >= 0
    assert settings.CHUNK_OVERLAP < settings.CHUNK_SIZE


# Add more tests as needed
