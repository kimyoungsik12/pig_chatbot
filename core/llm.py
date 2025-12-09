"""
vLLM LangChain integration for local Qwen model
"""
from langchain_openai import ChatOpenAI
from config import settings
from loguru import logger


def get_llm(temperature: float = None, max_tokens: int = None) -> ChatOpenAI:
    """
    Initialize LangChain LLM connected to local vLLM server

    Args:
        temperature: Override default temperature
        max_tokens: Override default max tokens

    Returns:
        ChatOpenAI: Configured LLM instance
    """
    temp = temperature if temperature is not None else settings.VLLM_TEMPERATURE
    max_tok = max_tokens if max_tokens is not None else settings.VLLM_MAX_TOKENS

    logger.info(f"Initializing LLM: {settings.VLLM_MODEL_NAME} at {settings.VLLM_BASE_URL}")

    llm = ChatOpenAI(
        model=settings.VLLM_MODEL_NAME,
        openai_api_base=settings.VLLM_BASE_URL,
        openai_api_key=settings.VLLM_API_KEY,
        temperature=temp,
        max_tokens=max_tok,
        streaming=False  # Set to True for streaming responses
    )

    logger.info("LLM initialized successfully")
    return llm


def get_streaming_llm(temperature: float = None, max_tokens: int = None) -> ChatOpenAI:
    """
    Get streaming-enabled LLM for real-time responses

    Args:
        temperature: Override default temperature
        max_tokens: Override default max tokens

    Returns:
        ChatOpenAI: Streaming LLM instance
    """
    temp = temperature if temperature is not None else settings.VLLM_TEMPERATURE
    max_tok = max_tokens if max_tokens is not None else settings.VLLM_MAX_TOKENS

    return ChatOpenAI(
        model=settings.VLLM_MODEL_NAME,
        openai_api_base=settings.VLLM_BASE_URL,
        openai_api_key=settings.VLLM_API_KEY,
        temperature=temp,
        max_tokens=max_tok,
        streaming=True
    )
