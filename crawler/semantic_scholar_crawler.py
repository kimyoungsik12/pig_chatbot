"""
Semantic Scholar crawler for pig-related papers (last 5 years).

Usage (module):
    python -m crawler.semantic_scholar_crawler --limit 10 --query "pig OR pig farm" --year_from 2020

Usage (script):
    python crawler/semantic_scholar_crawler.py --limit 10
"""
import argparse
import os
import json
import time
from datetime import datetime
from typing import List, Optional

import requests
from loguru import logger

# Allow running as script from repo root
if __name__ == "__main__" and __package__ is None:
    import sys

    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if ROOT_DIR not in sys.path:
        sys.path.append(ROOT_DIR)

from pipeline import ingest_from_text
from core import init_vectorstore


API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
CACHE_PATH = os.path.join(os.path.dirname(__file__), ".semantic_ingested.json")


def search_papers(query: str, year_from: int, limit: int, offset: int = 0) -> List[dict]:
    """Search Semantic Scholar for papers (one page)."""
    # Semantic Scholar caps limit around 100 per request
    effective_limit = 100 if limit == -1 or limit > 100 else limit
    params = {
        "query": query,
        "year": f"{year_from}-",  # from year_from to present
        "limit": effective_limit,
        "offset": offset,
        "fields": "paperId,title,abstract,year,authors,url,venue,openAccessPdf",
    }
    logger.info(f"Searching Semantic Scholar: {params}")

    # Retry with backoff for rate limits (429)
    backoff = 1.0
    while True:
        resp = requests.get(API_URL, params=params, timeout=30)
        if resp.status_code == 429:
            logger.warning(f"Rate limited (429). Sleeping {backoff:.1f}s and retrying...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)  # cap backoff
            continue
        if resp.status_code == 400:
            logger.info("Received 400 (likely offset beyond available results). Stopping pagination.")
            return []
        resp.raise_for_status()
        return resp.json().get("data", [])


def paper_to_text(paper: dict) -> str:
    """Convert paper metadata to a text blob (abstract only)."""
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


def ingest_papers(query: str, year_from: int, limit: int, page_delay: float = 1.0) -> int:
    """Fetch papers (paginated) and ingest their abstracts."""
    # Load cache of ingested paperIds to avoid duplicates across runs
    ingested_ids = set()
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                ingested_ids = set(json.load(f))
        except Exception:
            logger.warning("Failed to read cache; continuing without it.")

    total_chunks = 0
    new_ids = set()
    fetched = 0
    page_size = 100
    target_total = None if limit == -1 else limit
    offset = 0

    while True:
        # Respect target_total if set
        remaining = page_size if target_total is None else max(0, target_total - fetched)
        if target_total is not None and remaining == 0:
            break

        papers = search_papers(query=query, year_from=year_from, limit=remaining or page_size, offset=offset)
        if not papers:
            break

        for paper in papers:
            pid = paper.get("paperId")
            if pid and pid in ingested_ids:
                logger.info(f"Skipping already ingested paperId={pid}")
                continue

            text = paper_to_text(paper)
            metadata = {
                "title": paper.get("title") or "Untitled",
                "url": paper.get("url"),
                "source": "Semantic Scholar",
                "year": paper.get("year"),
                "venue": paper.get("venue"),
                "authors": [a.get("name") for a in paper.get("authors", [])],
                "paper_id": pid,
                "ingested_at": datetime.now().isoformat(),
            }
            chunks = ingest_from_text(text=text, metadata=metadata)
            total_chunks += chunks
            fetched += 1
            logger.info(f"Ingested '{metadata['title'][:50]}...' into {chunks} chunks (paper {fetched})")
            if pid:
                new_ids.add(pid)

            if target_total is not None and fetched >= target_total:
                break

        offset += len(papers)
        # rate limit friendly pause between pages
        if page_delay and page_delay > 0:
            time.sleep(page_delay)

    if fetched == 0:
        logger.warning("No papers ingested (empty result or all were duplicates).")

    # Persist updated cache
    if new_ids:
        try:
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(sorted(ingested_ids | new_ids), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")

    return total_chunks


def main():
    parser = argparse.ArgumentParser(description="Semantic Scholar pig paper crawler")
    parser.add_argument("--query", default="pig", help="Search query")
    parser.add_argument(
        "--year_from",
        type=int,
        default=datetime.now().year - 10,
        help="Start year (inclusive)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=-1,
        help="Number of papers to fetch (-1 for all available, fetched in pages of 100)"
    )
    parser.add_argument(
        "--page_delay",
        type=float,
        default=1.0,
        help="Seconds to sleep between page requests (helps avoid 429 rate limits)",
    )
    args = parser.parse_args()

    # Ensure collection exists
    init_vectorstore(reset=False)

    chunks = ingest_papers(
        query=args.query,
        year_from=args.year_from,
        limit=args.limit,
        page_delay=args.page_delay,
    )
    logger.info(f"Total ingested chunks: {chunks}")


if __name__ == "__main__":
    main()
