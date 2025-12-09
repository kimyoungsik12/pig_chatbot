"""
Example scraper implementation

Copy this file and modify for specific websites
"""
from crawler.base_crawler import BaseCrawler, CrawledDocument
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime
from urllib.parse import urljoin
from loguru import logger
import re


class ExampleScraper(BaseCrawler):
    """
    Example scraper - modify this for your target website

    Instructions:
    1. Copy this file and rename (e.g., kppa_scraper.py for 한국양돈협회)
    2. Update BASE_URL to your target website
    3. Implement get_article_urls() to extract article links
    4. Implement parse_article() to extract article content
    """

    BASE_URL = "https://www.pigpeople.net/news/section_list_all.html"

    def __init__(self):
        super().__init__(name="Example Pig Farming Site")

    def get_article_urls(self) -> List[str]:
        """
        Extract article URLs from the site

        Crawl all sections (sec_no) and pages until no new articles appear.
        Stops when a section returns no new links (the site repeats the last
        valid page when sec_no exceeds the maximum).
        """
        base_domain = "https://www.pigpeople.net"
        seen_urls = set()
        article_links: List[str] = []

        max_sections = 200  # safety guard against infinite loops
        sec_no = 1
        empty_sections_in_a_row = 0

        while sec_no <= max_sections:
            page = 1
            section_added = False

            while True:
                list_url = f"{self.BASE_URL}?sec_no={sec_no}&page={page}"
                html = self.fetch_html(list_url)
                if not html:
                    break

                soup = BeautifulSoup(html, "html.parser")
                page_links = []
                for link in soup.select("ul.art_list_all li a"):
                    href = link.get("href")
                    if not href:
                        continue
                    if href.startswith("/"):
                        href = urljoin(base_domain, href)
                    elif not href.startswith("http"):
                        href = urljoin(base_domain, href)
                    page_links.append(href)

                if not page_links:
                    break

                new_links = [u for u in page_links if u not in seen_urls]
                if not new_links:
                    # No new links on this page; likely repeated last page
                    break

                seen_urls.update(new_links)
                article_links.extend(new_links)
                section_added = True

                page += 1

            if section_added:
                empty_sections_in_a_row = 0
            else:
                empty_sections_in_a_row += 1
                # Stop after hitting consecutive empty sections (no new urls)
                if empty_sections_in_a_row >= 2:
                    break

            sec_no += 1

        logger.info(f"Found {len(article_links)} article URLs across sections/pages")
        return article_links

    def parse_article(self, url: str) -> Optional[CrawledDocument]:
        """
        Parse individual article content

        Target site structure (pigpeople.net):
        - Title: div.art_top > h2
        - Published date: ul.art_info > li contains "등록 2022.08.30 00:15:01"
        - Body: div#news_body_area (inside .cnt_view.news_body_area)
        """
        html = self.fetch_html(url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Title
            title_elem = soup.select_one("div.art_top h2") or soup.select_one("h1")
            title = title_elem.get_text(strip=True) if title_elem else "제목 없음"

            # Body content
            content_elem = soup.select_one("#news_body_area") or soup.select_one("div.cnt_view.news_body_area")
            if not content_elem:
                logger.warning(f"No content found for {url}")
                return None

            # Remove non-text elements
            for tag in content_elem.find_all(["script", "style"]):
                tag.decompose()

            raw_lines = content_elem.get_text(separator="\n", strip=True).splitlines()
            content_lines = [line.strip() for line in raw_lines if line.strip()]
            content = "\n".join(content_lines)

            # Published date
            date_text = None
            for li in soup.select("ul.art_info li"):
                text = li.get_text(" ", strip=True)
                if "등록" in text or "작성" in text or "입력" in text:
                    date_text = text
                    break

            if not date_text:
                meta_date = soup.select_one("meta[property='article:published_time']")
                if meta_date:
                    date_text = meta_date.get("content")

            published_date = None
            if date_text:
                match = re.search(r"(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})\s*(\d{2}:\d{2}(?::\d{2})?)?", date_text)
                if match:
                    date_part = match.group(1).replace(".", "-").replace("/", "-")
                    time_part = match.group(2)
                    if time_part:
                        if len(time_part.split(":")) == 2:
                            time_part = f"{time_part}:00"
                        try:
                            published_date = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            pass
                    else:
                        try:
                            published_date = datetime.strptime(date_part, "%Y-%m-%d")
                        except ValueError:
                            pass

            # Create document
            doc = CrawledDocument(
                title=title,
                content=content,
                url=url,
                source=self.name,
                published_date=published_date,
                metadata={
                    "word_count": len(content.split()),
                    "html_length": len(html),
                    "raw_date": date_text
                }
            )

            return doc

        except Exception as e:
            logger.error(f"Error parsing article {url}: {e}")
            return None


# Usage example:
if __name__ == "__main__":
    scraper = ExampleScraper()
    documents = scraper.crawl()
    print(f"Crawled {len(documents)} documents")
    for doc in documents[:3]:  # Print first 3
        print(doc)
