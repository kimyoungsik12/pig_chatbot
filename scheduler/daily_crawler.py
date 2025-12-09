"""
Daily crawler scheduler for automated document updates
"""
import schedule
import time
from datetime import datetime
from typing import List
from loguru import logger

from config import settings
from crawler.base_crawler import BaseCrawler
from pipeline import ingest_from_crawler


def crawl_and_ingest(crawlers: List[BaseCrawler]):
    """
    Execute crawl and ingest for all registered crawlers

    Args:
        crawlers: List of crawler instances
    """
    logger.info("=" * 60)
    logger.info(f"Starting scheduled crawl at {datetime.now()}")
    logger.info("=" * 60)

    total_crawled = 0
    total_ingested = 0

    for crawler in crawlers:
        try:
            logger.info(f"Running crawler: {crawler.name}")

            # Crawl documents
            documents = crawler.crawl()
            total_crawled += len(documents)

            # Ingest to vector store
            if documents:
                count = ingest_from_crawler(documents)
                total_ingested += count
                logger.info(f"Ingested {count} chunks from {crawler.name}")
            else:
                logger.warning(f"No documents crawled from {crawler.name}")

        except Exception as e:
            logger.error(f"Error processing crawler {crawler.name}: {e}")
            continue

    logger.info("=" * 60)
    logger.info(f"Scheduled crawl complete:")
    logger.info(f"  - Total documents crawled: {total_crawled}")
    logger.info(f"  - Total chunks ingested: {total_ingested}")
    logger.info("=" * 60)


def run_once(crawlers: List[BaseCrawler]):
    """
    Run crawl once immediately

    Args:
        crawlers: List of crawler instances
    """
    logger.info("Running one-time crawl...")
    crawl_and_ingest(crawlers)


def run_scheduler(crawlers: List[BaseCrawler]):
    """
    Run the scheduler continuously

    Args:
        crawlers: List of crawler instances to schedule
    """
    if not crawlers:
        logger.error("No crawlers provided to scheduler")
        return

    logger.info(f"Starting scheduler with {len(crawlers)} crawler(s)")
    logger.info(f"Scheduled time: {settings.CRAWLER_SCHEDULE_TIME} daily")

    # Register crawlers
    for crawler in crawlers:
        logger.info(f"  - {crawler.name}")

    # Schedule daily crawl
    schedule.every().day.at(settings.CRAWLER_SCHEDULE_TIME).do(
        crawl_and_ingest,
        crawlers=crawlers
    )

    logger.info("Scheduler started. Press Ctrl+C to stop.")
    logger.info(f"Next run: {schedule.next_run()}")

    # Run immediately on startup (optional)
    # crawl_and_ingest(crawlers)

    # Main scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        raise


# Example usage
if __name__ == "__main__":
    from crawler.example_scraper import ExampleScraper

    # Register your crawlers here
    crawlers = [
        ExampleScraper(),
        # Add more crawlers as needed
    ]

    # Run once or run scheduler
    # run_once(crawlers)  # For testing
    run_scheduler(crawlers)  # For production
