import unittest
from core.parser import parse_html
from core.scrapers.quotes_scraper import QuotesScraper
from core.scrapers.ecommerce_scraper import EcommerceScraper
from core.scrapers.dynamic_generic import DynamicGenericScraper


class TestScrapers(unittest.TestCase):
    def test_quotes_scraper(self):
        html = """
        <html>
            <body>
                <div class="quote">
                    <span class="text">“The world as we have created it is a process of our thinking.”</span>
                    <span>by <small class="author">Albert Einstein</small>
                    <a href="/author/Albert-Einstein">(about)</a>
                    </span>
                    <div class="tags">
                        <a class="tag" href="/tag/change/">change</a>
                        <a class="tag" href="/tag/deep-thoughts/">deep-thoughts</a>
                    </div>
                </div>
            </body>
        </html>
        """
        soup = parse_html(html)
        scraper = QuotesScraper()
        results = scraper.parse(soup, url="https://quotes.toscrape.com/js/", config={})

        self.assertEqual(len(results), 1)
        item = results[0]
        self.assertIn("The world as we have created it", item["quote"])
        self.assertEqual(item["author"], "Albert Einstein")
        self.assertEqual(item["author_url"], "https://quotes.toscrape.com/author/Albert-Einstein")
        self.assertEqual(item["tags"], ["change", "deep-thoughts"])

    def test_ecommerce_scraper(self):
        html = """
        <html>
            <body>
                <article class="product_pod">
                    <div class="image_container">
                        <a href="catalogue/a-light-in-the-attic_1000/index.html">
                            <img src="media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg" alt="A Light in the Attic">
                        </a>
                    </div>
                    <p class="star-rating Three"></p>
                    <h3><a href="catalogue/a-light-in-the-attic_1000/index.html" title="A Light in the Attic">A Light in the ...</a></h3>
                    <div class="product_price">
                        <p class="price_color">£51.77</p>
                        <p class="instock availability"><i class="icon-ok"></i> In stock</p>
                    </div>
                </article>
            </body>
        </html>
        """
        soup = parse_html(html)
        scraper = EcommerceScraper()
        results = scraper.parse(soup, url="https://books.toscrape.com/", config={})

        self.assertEqual(len(results), 1)
        prod = results[0]
        self.assertEqual(prod["title"], "A Light in the Attic")
        self.assertEqual(prod["price"], 51.77)
        self.assertTrue(prod["in_stock"])
        self.assertEqual(prod["rating"], 3)
        self.assertIn("books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html", prod["product_url"])

    def test_dynamic_generic_scraper(self):
        html = """
        <div class="articles">
            <div class="news-item">
                <h1 class="headline">Breaking Tech News</h1>
                <p class="summary">Major breakthrough in artificial intelligence announced today.</p>
                <a class="source" href="/source/reuters">Reuters</a>
            </div>
        </div>
        """
        soup = parse_html(html)
        scraper = DynamicGenericScraper()
        config = {
            "container_selector": ".news-item",
            "fields": {
                "headline": ".headline",
                "summary": ".summary",
                "source": ".source",
                "source_link": {"selector": ".source", "attribute": "href"},
            },
        }
        results = scraper.parse(soup, url="https://news.example.com", config=config)
        self.assertEqual(len(results), 1)
        news = results[0]
        self.assertEqual(news["headline"], "Breaking Tech News")
        self.assertEqual(news["source_link"], "https://news.example.com/source/reuters")


if __name__ == "__main__":
    unittest.main()

