import unittest
from bs4 import BeautifulSoup
from core.parser import parse_html, clean_text, extract_field, extract_list


class TestParser(unittest.TestCase):
    def setUp(self):
        self.html = """
        <div class="card">
            <h2 class="title">   Example Title   With   Spaces  </h2>
            <a class="main-link" href="/target-page">Read More</a>
            <div class="tags">
                <span class="tag">tech</span>
                <span class="tag">python</span>
                <span class="tag">automation</span>
            </div>
        </div>
        """
        self.soup = parse_html(self.html)
        self.card = self.soup.select_one(".card")

    def test_clean_text(self):
        self.assertEqual(clean_text("  hello   world  "), "hello world")
        self.assertEqual(clean_text(None), "")
        self.assertEqual(clean_text("\n\t  line1 \n line2  "), "line1 line2")

    def test_extract_field(self):
        title = extract_field(self.card, ".title")
        self.assertEqual(title, "Example Title With Spaces")

        href = extract_field(self.card, ".main-link", attribute="href")
        self.assertEqual(href, "/target-page")

        missing = extract_field(self.card, ".does-not-exist", default="N/A")
        self.assertEqual(missing, "N/A")

    def test_extract_list(self):
        tags = extract_list(self.card, ".tags .tag")
        self.assertEqual(tags, ["tech", "python", "automation"])


if __name__ == "__main__":
    unittest.main()

