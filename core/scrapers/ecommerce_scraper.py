import re
from typing import Any, Dict, List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from core.parser import clean_text, extract_field
from core.scrapers.base import BaseScraper

STAR_MAPPING = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


class EcommerceScraper(BaseScraper):
    """Scrapes product listings from e-commerce catalog pages."""

    scraper_type = "ecommerce"

    def parse(
        self,
        soup: BeautifulSoup,
        url: str,
        config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        items = []
        product_elements = soup.select("article.product_pod, .product-item, .product-card")

        for pod in product_elements:
            # Title
            title = (
                extract_field(pod, "h3 a", attribute="title")
                or extract_field(pod, "h3 a")
                or extract_field(pod, ".product-title")
            )

            # Price
            raw_price = extract_field(pod, ".price_color, .price, .product-price")
            price_match = re.search(r"[\d\.]+", raw_price)
            price = float(price_match.group(0)) if price_match else None

            # Availability
            availability = extract_field(pod, ".availability, .stock-status")
            in_stock = "in stock" in availability.lower() if availability else True

            # Rating
            rating = None
            rating_el = pod.select_one(".star-rating")
            if rating_el:
                classes = [c.lower() for c in rating_el.get("class", [])]
                for word, stars in STAR_MAPPING.items():
                    if word in classes:
                        rating = stars
                        break

            # Product URL
            rel_link = extract_field(pod, "h3 a, a.product-link", attribute="href")
            product_url = urljoin(url, rel_link) if rel_link else ""

            # Image URL
            rel_img = extract_field(pod, "img", attribute="src")
            image_url = urljoin(url, rel_img) if rel_img else ""

            if title:
                items.append({
                    "title": title,
                    "price": price,
                    "raw_price": raw_price,
                    "in_stock": in_stock,
                    "rating": rating,
                    "product_url": product_url,
                    "image_url": image_url,
                    "source_url": url,
                })

        return items

