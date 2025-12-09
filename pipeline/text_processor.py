"""
Text processing and chunking for Korean documents
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from config import settings
from loguru import logger
from typing import List


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """
    Get Korean-optimized text splitter

    Returns:
        RecursiveCharacterTextSplitter: Configured text splitter
    """
    # Korean-optimized separators
    separators = [
        "\n\n",  # Paragraphs
        "\n",    # Lines
        "。",    # Full stop (sometimes used in Korean)
        ". ",    # English period
        "! ",    # Exclamation
        "? ",    # Question
        " ",     # Space
        ""       # Character-level fallback
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=separators,
        length_function=len,
        is_separator_regex=False
    )

    return splitter


def process_document(
    content: str,
    metadata: dict = None,
    splitter: RecursiveCharacterTextSplitter = None
) -> List[Document]:
    """
    Process a document into chunks with metadata

    Args:
        content: Document text content
        metadata: Document metadata
        splitter: Optional text splitter (uses default if None)

    Returns:
        List[Document]: List of chunked documents with metadata
    """
    if splitter is None:
        splitter = get_text_splitter()

    # Clean content
    content = content.strip()
    if not content:
        logger.warning("Empty content provided")
        return []

    # Split into chunks
    chunks = splitter.split_text(content)
    logger.info(f"Split document into {len(chunks)} chunks")

    # Create Document objects with metadata
    documents = []
    for i, chunk in enumerate(chunks):
        doc_metadata = metadata.copy() if metadata else {}
        doc_metadata.update({
            "chunk_index": i,
            "total_chunks": len(chunks),
            "chunk_size": len(chunk)
        })

        doc = Document(
            page_content=chunk,
            metadata=doc_metadata
        )
        documents.append(doc)

    return documents


def validate_document_quality(content: str) -> bool:
    """
    Basic quality validation for documents

    Args:
        content: Document content

    Returns:
        bool: True if document meets quality standards
    """
    # Minimum length check
    if len(content.strip()) < 100:
        logger.warning("Document too short (< 100 chars)")
        return False

    # Check if mostly Korean text
    korean_chars = sum(1 for c in content if '\uac00' <= c <= '\ud7a3')
    total_chars = len(content.replace(" ", "").replace("\n", ""))

    if total_chars > 0:
        korean_ratio = korean_chars / total_chars
        if korean_ratio < 0.3:  # At least 30% Korean
            logger.warning(f"Low Korean content ratio: {korean_ratio:.2%}")
            return False

    return True
