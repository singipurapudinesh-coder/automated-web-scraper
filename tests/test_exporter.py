import os
import tempfile
import unittest
import pandas as pd
import database
import exporter


class TestExporter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_export.db")
        database.init_db(self.db_path)

        # Seed data
        self.job_id = database.add_or_update_job(
            name="export_job",
            url="https://example.com",
            scraper_type="quotes",
            db_path=self.db_path,
        )
        self.run_id = database.record_run_start(self.job_id, db_path=self.db_path)
        sample_items = [
            {"quote": "Quote 1", "author": "Author A", "tags": ["tag1", "tag2"]},
            {"quote": "Quote 2", "author": "Author B", "tags": ["tag3"]},
        ]
        database.save_scraped_items(self.job_id, self.run_id, sample_items, db_path=self.db_path)
        database.record_run_finish(self.run_id, "success", 2, db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_export_to_csv(self):
        csv_file = os.path.join(self.temp_dir.name, "test_output.csv")
        out_path = exporter.export_to_csv(
            job_id=self.job_id,
            output_path=csv_file,
            db_path=self.db_path,
        )
        self.assertTrue(os.path.exists(out_path))

        df = pd.read_csv(out_path)
        self.assertEqual(len(df), 2)
        self.assertIn("quote", df.columns)
        self.assertIn("author", df.columns)
        self.assertIn("tags", df.columns)
        self.assertEqual(df.iloc[0]["tags"], "tag1, tag2")

    def test_export_to_json(self):
        json_file = os.path.join(self.temp_dir.name, "test_output.json")
        out_path = exporter.export_to_json(
            job_id=self.job_id,
            output_path=json_file,
            db_path=self.db_path,
        )
        self.assertTrue(os.path.exists(out_path))

        with open(out_path, "r", encoding="utf-8") as f:
            import json
            data = json.load(f)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["author"], "Author A")


if __name__ == "__main__":
    unittest.main()

