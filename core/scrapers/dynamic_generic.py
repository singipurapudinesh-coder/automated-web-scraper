from typing import Any, Dict, List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from core.parser import clean_text, extract_field, extract_list
from core.scrapers.base import BaseScraper


class DynamicGenericScraper(BaseScraper):
    """Config-driven dynamic scraper capable of scraping arbitrary websites using CSS selectors."""

    scraper_type = "dynamic_generic"

    def parse(
        self,
        soup: BeautifulSoup,
        url: str,
        config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        container_selector = config.get("container_selector")
        if not container_selector:
            # If no container specified, return top-level metadata
            return [{
                "title": clean_text(soup.title.string if soup.title else ""),
                "source_url": url,
            }]

        containers = soup.select(container_selector)
        fields_config = config.get("fields", {})
        items = []

        for container in containers:
            record: Dict[str, Any] = {"source_url": url}

            for field_name, rule in fields_config.items():
                if isinstance(rule, str):
                    # Shorthand: CSS selector extracting clean text
                    record[field_name] = extract_field(container, rule)
                elif isinstance(rule, dict):
                    sel = rule.get("selector", "")
                    attr = rule.get("attribute")
                    field_type = rule.get("type", "text")

                    if field_type == "list":
                        record[field_name] = extract_list(container, sel, attribute=attr)
                    else:
                        val = extract_field(container, sel, attribute=attr)
                        # If extracting a relative URL, resolve against page URL
                        if attr in ("href", "src") and isinstance(val, str) and val:
                            val = urljoin(url, val)
                        record[field_name] = val

            if any(v for k, v in record.items() if k != "source_url"):
                items.append(record)

        return items

