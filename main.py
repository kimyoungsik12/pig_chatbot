"""
Main entry point for Pig Farming RAG LLM System
"""
import argparse
import sys
from loguru import logger

from config import settings


def setup_logging():
    """Configure logging"""
    logger.remove()  # Remove default handler

    # Console logging
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )

    # File logging
    if settings.LOG_FILE:
        logger.add(
            settings.LOG_FILE,
            rotation="10 MB",
            retention="30 days",
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
        )


def run_api():
    """Run FastAPI server"""
    import uvicorn
    from api.server import app

    logger.info("Starting API server...")
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower()
    )


def run_scheduler_mode():
    """Run crawler scheduler"""
    from scheduler import run_scheduler
    from crawler.example_scraper import ExampleScraper

    logger.info("Starting crawler scheduler...")

    # Register your crawlers here
    crawlers = [
        ExampleScraper(),
        # Add more site-specific crawlers as you implement them
    ]

    run_scheduler(crawlers)


def run_test_query(question: str):
    """Run a test query"""
    from rag import get_qa_chain

    logger.info(f"Testing query: {question}")

    chain = get_qa_chain()
    result = chain.invoke({"query": question})

    print("\n" + "=" * 60)
    print("ANSWER:")
    print("=" * 60)
    print(result["result"])
    print("\n" + "=" * 60)
    print("SOURCE DOCUMENTS:")
    print("=" * 60)

    for i, doc in enumerate(result.get("source_documents", []), 1):
        print(f"\n[{i}] {doc.metadata.get('title', 'No title')}")
        print(f"    URL: {doc.metadata.get('url', 'N/A')}")
        print(f"    Content: {doc.page_content[:200]}...")


def init_vectorstore_cmd(reset: bool = False):
    """Initialize vector store"""
    from core import init_vectorstore

    logger.info(f"Initializing vectorstore (reset={reset})...")
    init_vectorstore(reset=reset)
    logger.info("Vectorstore initialized successfully")


def crawl_once():
    """Run crawler once"""
    from scheduler import run_once
    from crawler.example_scraper import ExampleScraper

    logger.info("Running one-time crawl...")

    crawlers = [
        ExampleScraper(),
    ]

    run_once(crawlers)
    logger.info("Crawl complete")


def main():
    """Main CLI entry point"""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="한국 양돈 전문 RAG LLM System"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # API server
    subparsers.add_parser("api", help="Run API server")

    # Scheduler
    subparsers.add_parser("scheduler", help="Run crawler scheduler")

    # One-time crawl
    subparsers.add_parser("crawl", help="Run crawler once")

    # Initialize vectorstore
    init_parser = subparsers.add_parser("init", help="Initialize vectorstore")
    init_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset existing collection"
    )

    # Test query
    query_parser = subparsers.add_parser("query", help="Test a query")
    query_parser.add_argument("question", help="Question to ask")

    args = parser.parse_args()

    # Execute command
    if args.command == "api":
        run_api()
    elif args.command == "scheduler":
        run_scheduler_mode()
    elif args.command == "crawl":
        crawl_once()
    elif args.command == "init":
        init_vectorstore_cmd(reset=args.reset)
    elif args.command == "query":
        run_test_query(args.question)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
