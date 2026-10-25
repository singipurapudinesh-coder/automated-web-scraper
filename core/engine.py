import logging
import time
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import config

logger = logging.getLogger(__name__)


class BrowserEngine:
    """Manages Selenium WebDriver lifecycle, dynamic waits, and page interactions."""

    def __init__(
        self,
        headless: bool = config.SELENIUM_HEADLESS,
        timeout: int = config.SELENIUM_TIMEOUT,
        user_agent: str = config.USER_AGENT,
    ):
        self.headless = headless
        self.timeout = timeout
        self.user_agent = user_agent
        self.driver: Optional[webdriver.Chrome] = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self) -> webdriver.Chrome:
        """Initializes and configures the Chrome WebDriver."""
        if self.driver is not None:
            return self.driver

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")

        # Performance & Anti-detection flags
        options.add_argument(f"--user-agent={self.user_agent}")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(self.timeout * 2)
            # Remove navigator.webdriver flag in JS
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
            )
            return self.driver
        except Exception as e:
            logger.error(f"Failed to start Chrome WebDriver: {e}")
            raise

    def stop(self) -> None:
        """Closes the browser session safely."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error while closing driver: {e}")
            finally:
                self.driver = None

    def get_rendered_html(
        self,
        url: str,
        wait_selector: Optional[str] = None,
        scroll_down: bool = False,
        scroll_pause_sec: float = 1.0,
        max_scrolls: int = 3,
    ) -> str:
        """Navigates to the given URL, handles dynamic rendering/scrolling, and returns the HTML."""
        if not self.driver:
            self.start()

        assert self.driver is not None
        logger.info(f"Navigating to {url}")
        self.driver.get(url)

        # Explicit wait for a target selector if provided
        if wait_selector:
            try:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
            except Exception as e:
                logger.warning(f"Timeout waiting for selector '{wait_selector}' on {url}: {e}")

        # Infinite scroll handling for dynamic pages
        if scroll_down:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            for _ in range(max_scrolls):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_sec)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

        return self.driver.page_source

