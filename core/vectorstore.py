"""
Qdrant vector store integration
"""
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from config import settings
from core.embeddings import get_embeddings, get_embedding_dimension
from loguru import logger
from typing import Optional
import types


def get_qdrant_client() -> QdrantClient:
    """
    Get Qdrant client connection

    Returns:
        QdrantClient: Connected Qdrant client
    """
    logger.info(f"Connecting to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")

    client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        timeout=30
    )
    if not hasattr(client, "search"):
        logger.warning("QdrantClient.search not found; adding compatibility shim via query_points()")

        def _search(self, collection_name, query_vector=None, query=None, query_text=None, limit=10, with_payload=True, **kwargs):
            # Map LangChain args to qdrant-client query_points
            search_params = kwargs.pop("search_params", None)
            # Some callers use "params"; map to search_params
            if "params" in kwargs and search_params is None:
                search_params = kwargs.pop("params")
            else:
                kwargs.pop("params", None)
            score_threshold = kwargs.pop("score_threshold", None)
            q = query_text or query or query_vector
            if q is None:
                raise ValueError("query/search called without query_text or query_vector")
            resp = self.query_points(
                collection_name=collection_name,
                query=q,
                limit=limit,
                with_payload=with_payload,
                score_threshold=score_threshold,
                search_params=search_params,
                **kwargs
            )
            # QueryResponse has 'points' attribute, not 'result'
            # Return list of ScoredPoint objects that LangChain expects
            if hasattr(resp, "points"):
                return resp.points
            elif hasattr(resp, "result"):
                return resp.result
            else:
                return resp

        client.search = types.MethodType(_search, client)

    logger.info("Qdrant client connected successfully")
    return client


def init_vectorstore(reset: bool = False) -> None:
    """
    Initialize Qdrant collection if it doesn't exist

    Args:
        reset: If True, delete existing collection and recreate
    """
    client = get_qdrant_client()
    collection_name = settings.QDRANT_COLLECTION_NAME

    try:
        # Check if collection exists
        collections = client.get_collections().collections
        exists = any(col.name == collection_name for col in collections)

        if exists and reset:
            logger.warning(f"Deleting existing collection: {collection_name}")
            client.delete_collection(collection_name)
            exists = False

        if not exists:
            logger.info(f"Creating new collection: {collection_name}")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=get_embedding_dimension(),
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Collection created: {collection_name}")
        else:
            logger.info(f"Collection already exists: {collection_name}")

    except Exception as e:
        logger.error(f"Error initializing vectorstore: {e}")
        raise


def get_vectorstore(client: Optional[QdrantClient] = None) -> Qdrant:
    """
    Get LangChain Qdrant vectorstore instance

    Args:
        client: Optional existing Qdrant client

    Returns:
        Qdrant: LangChain Qdrant vectorstore
    """
    if client is None:
        client = get_qdrant_client()

    embeddings = get_embeddings()

    vectorstore = Qdrant(
        client=client,
        collection_name=settings.QDRANT_COLLECTION_NAME,
        embeddings=embeddings
    )

    logger.info("Vectorstore initialized successfully")
    return vectorstore
