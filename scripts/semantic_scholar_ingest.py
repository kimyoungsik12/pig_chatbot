"""
Fetch a recent pig-related paper from Semantic Scholar and ingest into vector store.

Usage:
    python scripts/semantic_scholar_ingest.py
"""
import os
import sys
from datetime import datetime
from typing import Optional

import requests
from loguru import logger

# Ensure project root is in PYTHONPATH when running as a script or under debugger
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from config import settings
from pipeline import ingest_from_text
from core import init_vectorstore


SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def search_paper(query: str, year_from: int, limit: int = 1) -> Optional[dict]:
    """Search Semantic Scholar for a paper."""
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,year,authors,url,venue,openAccessPdf",
        "year": f"{year_from}-",  # from year_from to present
    }
    logger.info(f"Searching Semantic Scholar: {params}")
    resp = requests.get(SEMANTIC_SCHOLAR_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    papers = data.get("data", [])
    return papers[0] if papers else None


def to_text(paper: dict) -> str:
    """Build a text blob from paper metadata."""
    title = paper.get("title") or ""
    abstract = paper.get("abstract") or ""
    authors = ", ".join([a.get("name", "") for a in paper.get("authors", [])])
    venue = paper.get("venue") or ""
    year = paper.get("year") or ""
    lines = [
        f"Title: {title}",
        f"Authors: {authors}",
        f"Venue/Year: {venue} ({year})",
        f"URL: {paper.get('url','')}",
        "",
        "Abstract:",
        abstract,
    ]
    return "\n".join(lines)


def ingest_one_paper(query: str, year_from: int) -> None:
    paper = search_paper(query, year_from, limit=1)
    if not paper:
        logger.error("No paper found for query.")
        return

    text = to_text(paper)
    metadata = {
        "title": paper.get("title") or "Untitled",
        "url": paper.get("url"),
        "source": "Semantic Scholar",
        "year": paper.get("year"),
        "venue": paper.get("venue"),
        "authors": [a.get("name") for a in paper.get("authors", [])],
        "ingested_at": datetime.now().isoformat(),
    }

    logger.info(f"Ingesting paper: {metadata['title']}")
    chunks = ingest_from_text(text=text, metadata=metadata)
    logger.info(f"Ingested chunks: {chunks}")


def main():
    # Ensure vector store exists
    init_vectorstore(reset=False)

    current_year = datetime.now().year
    year_from = current_year - 5

    # Test query: pig OR pig farm
    ingest_one_paper(query="pig OR pig farm", year_from=year_from)


if __name__ == "__main__":
    main()
