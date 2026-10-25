from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from core.engine import BrowserEngine
from core.parser import parse_html


class BaseScraper(ABC):
    """Abstract base class for all scraper implementations."""

    scraper_type: str = "base"

    def __init__(self, browser_engine: Optional[BrowserEngine] = None):
        self.engine = browser_engine

    def scrape(
        self,
        url: str,
        config: Optional[Dict[str, Any]] = None,
        max_pages: int = 1,
    ) -> List[Dict[str, Any]]:
        """Orchestrates page loading (via dynamic Selenium) and parsing (via BeautifulSoup)."""
        cfg = config or {}
        wait_selector = cfg.get("wait_selector")
        scroll_down = cfg.get("scroll_down", False)

        # Use passed browser engine or instantiate one
        if self.engine:
            html = self.engine.get_rendered_html(
                url,
                wait_selector=wait_selector,
                scroll_down=scroll_down,
            )
        else:
            with BrowserEngine() as engine:
                html = engine.get_rendered_html(
                    url,
                    wait_selector=wait_selector,
                    scroll_down=scroll_down,
                )

        soup = parse_html(html)
        return self.parse(soup, url=url, config=cfg)

    @abstractmethod
    def parse(
        self,
        soup: BeautifulSoup,
        url: str,
        config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Parses the rendered DOM using BeautifulSoup and returns extracted structured records."""
        pass

