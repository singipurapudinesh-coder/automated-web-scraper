import os
import tempfile
import unittest
import database
import exporter
from core.scrapers import get_scraper


class TestLiveScraping(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "live_test.db")
        database.init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_live_quotes_scraping(self):
        # 1. Add job to SQLite
        job_id = database.add_or_update_job(
            name="live_quotes",
            url="https://quotes.toscrape.com/js/",
            scraper_type="quotes",
            schedule_interval_minutes=60,
            config={"wait_selector": ".quote"},
            db_path=self.db_path,
        )

        # 2. Record run start
        run_id = database.record_run_start(job_id, db_path=self.db_path)

        # 3. Scrape using Selenium (Dynamic JS rendering) + BeautifulSoup (Extraction)
        scraper = get_scraper("quotes")
        items = scraper.scrape("https://quotes.toscrape.com/js/", config={"wait_selector": ".quote"})

        self.assertGreater(len(items), 0, "Should have scraped at least one quote from dynamic page")
        self.assertIn("quote", items[0])
        self.assertIn("author", items[0])

        # 4. Save items to SQLite with deduplication
        saved_count = database.save_scraped_items(job_id, run_id, items, db_path=self.db_path)
        database.record_run_finish(run_id, "success", saved_count, db_path=self.db_path)

        # 5. Verify records in database
        db_items = database.get_scraped_items(job_id=job_id, db_path=self.db_path)
        self.assertEqual(len(db_items), len(items))

        # 6. Export to CSV
        csv_path = os.path.join(self.temp_dir.name, "quotes.csv")
        exporter.export_to_csv(job_id=job_id, output_path=csv_path, db_path=self.db_path)
        self.assertTrue(os.path.exists(csv_path))
        self.assertGreater(os.path.getsize(csv_path), 50)


if __name__ == "__main__":
    unittest.main()

