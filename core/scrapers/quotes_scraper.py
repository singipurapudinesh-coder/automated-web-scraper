from typing import Any, Dict, List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from core.parser import clean_text, extract_field, extract_list
from core.scrapers.base import BaseScraper


class QuotesScraper(BaseScraper):
    """Scraper tailored for dynamic quote sites like quotes.toscrape.com/js/."""

    scraper_type = "quotes"

    def parse(
        self,
        soup: BeautifulSoup,
        url: str,
        config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        items = []
        quote_elements = soup.select(".quote")

        for el in quote_elements:
            text = extract_field(el, ".text")
            author = extract_field(el, ".author")
            author_rel_link = extract_field(el, "span a", attribute="href")
            author_url = urljoin(url, author_rel_link) if author_rel_link else ""
            tags = extract_list(el, ".tags .tag")

            if text:
                items.append({
                    "quote": text,
                    "author": author,
                    "author_url": author_url,
                    "tags": tags,
                    "source_url": url,
                })

        return items

