"""
Document ingestion pipeline to vector store
"""
import time
from typing import List
from langchain_core.documents import Document
from crawler.base_crawler import BaseCrawler, CrawledDocument
from pipeline.text_processor import process_document, get_text_splitter, validate_document_quality
from core import get_vectorstore
from loguru import logger


def ingest_documents(
    documents: List[Document],
    vectorstore=None,
    batch_size: int = 100,
    max_retries: int = -1,
    retry_backoff: float = 1.0
) -> int:
    """
    Ingest documents into vector store

    Args:
        documents: List of LangChain Document objects
        vectorstore: Optional vectorstore instance
        batch_size: Batch size for ingestion

    Returns:
        int: Number of documents successfully ingested
    """
    if not documents:
        logger.warning("No documents to ingest")
        return 0

    if vectorstore is None:
        vectorstore = get_vectorstore()

    logger.info(f"Ingesting {len(documents)} document chunks...")

    try:
        # Batch processing for efficiency
        total_ingested = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            # Retry on transient errors (network drop, etc.)
            attempt = 1
            while True:
                try:
                    vectorstore.add_documents(batch)
                    total_ingested += len(batch)
                    logger.info(f"Ingested batch {i // batch_size + 1}: {len(batch)} chunks")
                    break
                except Exception as e:
                    if max_retries != -1 and attempt >= max_retries:
                        logger.error(f"Batch ingest failed after {attempt} attempts; aborting.")
                        raise
                    logger.warning(f"Batch ingest failed (attempt {attempt}/{max_retries if max_retries != -1 else '∞'}): {e}")
                    time.sleep(retry_backoff * attempt)  # simple linear backoff
                    attempt += 1

        logger.info(f"Successfully ingested {total_ingested} document chunks")
        return total_ingested

    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        raise


def ingest_from_crawler(
    crawled_docs: List[CrawledDocument],
    vectorstore=None,
    validate_quality: bool = True
) -> int:
    """
    Ingest crawled documents into vector store

    Args:
        crawled_docs: List of CrawledDocument objects from crawler
        vectorstore: Optional vectorstore instance
        validate_quality: Whether to validate document quality

    Returns:
        int: Number of documents successfully ingested
    """
    logger.info(f"Processing {len(crawled_docs)} crawled documents")

    splitter = get_text_splitter()
    all_chunks = []

    for crawled_doc in crawled_docs:
        # Quality validation
        if validate_quality and not validate_document_quality(crawled_doc.content):
            logger.warning(f"Skipping low-quality document: {crawled_doc.title}")
            continue

        # Prepare metadata
        metadata = {
            "title": crawled_doc.title,
            "url": crawled_doc.url,
            "source": crawled_doc.source,
            "published_date": crawled_doc.published_date.isoformat(),
            "crawled_at": crawled_doc.crawled_at.isoformat(),
            **crawled_doc.metadata
        }

        # Process into chunks
        chunks = process_document(
            content=crawled_doc.content,
            metadata=metadata,
            splitter=splitter
        )

        all_chunks.extend(chunks)
        logger.info(
            f"Processed '{crawled_doc.title[:50]}...' "
            f"into {len(chunks)} chunks"
        )

    # Ingest all chunks
    if all_chunks:
        count = ingest_documents(all_chunks, vectorstore)
        logger.info(
            f"Ingestion complete: {len(crawled_docs)} documents → "
            f"{count} chunks in vector store"
        )
        return count
    else:
        logger.warning("No valid documents to ingest")
        return 0


def ingest_from_text(
    text: str,
    metadata: dict = None,
    vectorstore=None
) -> int:
    """
    Ingest plain text into vector store

    Args:
        text: Plain text content
        metadata: Optional metadata
        vectorstore: Optional vectorstore instance

    Returns:
        int: Number of chunks ingested
    """
    chunks = process_document(text, metadata or {})
    if chunks:
        return ingest_documents(chunks, vectorstore)
    return 0
