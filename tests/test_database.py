import os
import tempfile
import unittest
import database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        database.init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_job_crud(self):
        job_id = database.add_or_update_job(
            name="test_job",
            url="https://example.com",
            scraper_type="quotes",
            schedule_interval_minutes=15,
            config={"wait_selector": ".quote"},
            db_path=self.db_path,
        )
        self.assertIsInstance(job_id, int)

        # Retrieve job by ID
        job = database.get_job(job_id, db_path=self.db_path)
        self.assertIsNotNone(job)
        self.assertEqual(job["name"], "test_job")
        self.assertEqual(job["schedule_interval_minutes"], 15)
        self.assertEqual(job["config"]["wait_selector"], ".quote")

        # Retrieve job by Name
        job_by_name = database.get_job("test_job", db_path=self.db_path)
        self.assertEqual(job_by_name["id"], job_id)

        # List jobs
        jobs = database.list_jobs(db_path=self.db_path)
        self.assertEqual(len(jobs), 1)

    def test_runs_and_items_with_deduplication(self):
        job_id = database.add_or_update_job(
            name="dedup_test",
            url="https://example.com/items",
            scraper_type="dynamic_generic",
            db_path=self.db_path,
        )

        run1_id = database.record_run_start(job_id, db_path=self.db_path)

        items_batch1 = [
            {"title": "Item A", "price": 10.99},
            {"title": "Item B", "price": 20.50},
        ]
        saved1 = database.save_scraped_items(job_id, run1_id, items_batch1, db_path=self.db_path)
        database.record_run_finish(run1_id, "success", saved1, db_path=self.db_path)
        self.assertEqual(saved1, 2)

        stored_items = database.get_scraped_items(job_id=job_id, db_path=self.db_path)
        self.assertEqual(len(stored_items), 2)

        # Run 2 with duplicate Item A and new Item C
        run2_id = database.record_run_start(job_id, db_path=self.db_path)
        items_batch2 = [
            {"title": "Item A", "price": 10.99},  # Duplicate
            {"title": "Item C", "price": 30.00},  # New
        ]
        database.save_scraped_items(job_id, run2_id, items_batch2, db_path=self.db_path)
        database.record_run_finish(run2_id, "success", 2, db_path=self.db_path)

        # Total items should be 3 (not 4) because Item A was deduplicated!
        all_items = database.get_scraped_items(job_id=job_id, db_path=self.db_path)
        self.assertEqual(len(all_items), 3)

        stats = database.get_job_stats(job_id, db_path=self.db_path)
        self.assertEqual(stats["total_items"], 3)
        self.assertEqual(stats["total_runs"], 2)
        self.assertEqual(stats["successful_runs"], 2)


if __name__ == "__main__":
    unittest.main()

