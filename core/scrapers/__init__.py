from typing import Dict, Optional, Type
from core.engine import BrowserEngine
from core.scrapers.base import BaseScraper
from core.scrapers.quotes_scraper import QuotesScraper
from core.scrapers.ecommerce_scraper import EcommerceScraper
from core.scrapers.dynamic_generic import DynamicGenericScraper

SCRAPER_REGISTRY: Dict[str, Type[BaseScraper]] = {
    "quotes": QuotesScraper,
    "ecommerce": EcommerceScraper,
    "dynamic_generic": DynamicGenericScraper,
}


def get_scraper(scraper_type: str, browser_engine: Optional[BrowserEngine] = None) -> BaseScraper:
    """Returns an instance of the requested scraper."""
    cls = SCRAPER_REGISTRY.get(scraper_type)
    if not cls:
        raise ValueError(
            f"Unknown scraper type: '{scraper_type}'. Available types: {list(SCRAPER_REGISTRY.keys())}"
        )
    return cls(browser_engine=browser_engine)

