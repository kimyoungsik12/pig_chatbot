"""
Base crawler class for pluggable site-specific scrapers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from config import settings
from loguru import logger
import time


class CrawledDocument:
    """Represents a crawled document"""

    def __init__(
        self,
        title: str,
        content: str,
        url: str,
        source: str,
        published_date: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ):
        self.title = title
        self.content = content
        self.url = url
        self.source = source
        self.published_date = published_date or datetime.now()
        self.metadata = metadata or {}
        self.crawled_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "source": self.source,
            "published_date": self.published_date.isoformat(),
            "crawled_at": self.crawled_at.isoformat(),
            "metadata": self.metadata
        }

    def __repr__(self):
        return f"<CrawledDocument: {self.title[:50]}... from {self.source}>"


class BaseCrawler(ABC):
    """
    Abstract base class for site-specific crawlers

    Subclass this to implement crawlers for specific websites
    """

    def __init__(self, name: str):
        self.name = name
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.CRAWLER_USER_AGENT
        })
        self.timeout = settings.CRAWLER_TIMEOUT
        self.max_retries = settings.CRAWLER_MAX_RETRIES

    @abstractmethod
    def get_article_urls(self) -> List[str]:
        """
        Get list of article URLs to crawl

        Returns:
            List[str]: List of article URLs
        """
        pass

    @abstractmethod
    def parse_article(self, url: str) -> Optional[CrawledDocument]:
        """
        Parse a single article from URL

        Args:
            url: Article URL

        Returns:
            CrawledDocument: Parsed document or None if failed
        """
        pass

    def fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from URL with retry logic

        Args:
            url: Target URL

        Returns:
            str: HTML content or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching URL (attempt {attempt + 1}/{self.max_retries}): {url}")
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text

            except requests.exceptions.RequestException as e:
                logger.warning(f"Fetch failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
                    return None

    def crawl(self) -> List[CrawledDocument]:
        """
        Execute full crawl process

        Returns:
            List[CrawledDocument]: List of successfully crawled documents
        """
        logger.info(f"Starting crawl for {self.name}")
        start_time = time.time()

        try:
            # Get article URLs
            urls = self.get_article_urls()
            logger.info(f"Found {len(urls)} articles to crawl")

            # Parse each article
            documents = []
            for i, url in enumerate(urls, 1):
                logger.info(f"Processing article {i}/{len(urls)}")

                doc = self.parse_article(url)
                if doc:
                    documents.append(doc)
                    logger.info(f"Successfully parsed: {doc.title[:50]}")
                else:
                    logger.warning(f"Failed to parse: {url}")

                # Rate limiting
                time.sleep(1)

            elapsed = time.time() - start_time
            logger.info(
                f"Crawl completed for {self.name}: "
                f"{len(documents)}/{len(urls)} successful "
                f"in {elapsed:.2f}s"
            )

            return documents

        except Exception as e:
            logger.error(f"Crawl failed for {self.name}: {e}")
            raise

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"
