import logging
import time
from datetime import datetime
from typing import Optional
import schedule

import database
from tasks.celery_tasks import execute_job_task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("StandaloneScheduler")


def run_job_sync(job_id: int):
    """Executes a scraping job synchronously without requiring Celery/Redis."""
    logger.info(f"Triggering scheduled execution for job_id={job_id}")
    res = execute_job_task(job_id)
    logger.info(f"Execution finished for job_id={job_id}: {res}")


class LocalScheduler:
    """Zero-dependency local scheduler using SQLite and Python schedule library."""

    def __init__(self, check_interval_sec: float = 1.0):
        self.check_interval_sec = check_interval_sec
        self.registered_jobs = set()

    def sync_jobs(self):
        """Reads active jobs from SQLite and sets up recurring intervals."""
        jobs = database.list_jobs(enabled_only=True)
        current_job_ids = {j["id"] for j in jobs}

        # Clear and rebuild schedule if jobs changed
        if current_job_ids != self.registered_jobs:
            logger.info("Syncing scheduler with updated SQLite jobs...")
            schedule.clear()
            self.registered_jobs = current_job_ids

            for job in jobs:
                job_id = job["id"]
                job_name = job["name"]
                cfg = job.get("config", {})

                # Allow second-level precision for testing and high-frequency monitoring
                sec_interval = cfg.get("schedule_interval_seconds")
                if sec_interval:
                    logger.info(
                        f"Registered job '{job_name}' (ID: {job_id}) to run recurringly every {sec_interval} second(s)."
                    )
                    schedule.every(int(sec_interval)).seconds.do(run_job_sync, job_id=job_id)
                else:
                    interval = max(1, job.get("schedule_interval_minutes", 60))
                    logger.info(
                        f"Registered job '{job_name}' (ID: {job_id}) to run recurringly every {interval} minute(s)."
                    )
                    schedule.every(interval).minutes.do(run_job_sync, job_id=job_id)

    def start(self, run_immediately: bool = True, max_duration_sec: Optional[float] = None):
        """Starts the scheduler blocking loop, optionally exiting after max_duration_sec."""
        database.init_db()
        logger.info("Initializing Local Scraper Scheduler...")
        self.sync_jobs()

        if run_immediately:
            logger.info("Running all active jobs once immediately on startup...")
            jobs = database.list_jobs(enabled_only=True)
            for j in jobs:
                run_job_sync(j["id"])

        logger.info("Scheduler active. Waiting for next recurring scheduled runs...")
        start_time = time.time()
        try:
            while True:
                # Refresh job definitions periodically in case user added/updated via CLI
                self.sync_jobs()
                schedule.run_pending()
                time.sleep(self.check_interval_sec)

                if max_duration_sec and (time.time() - start_time) >= max_duration_sec:
                    logger.info(f"Reached max duration of {max_duration_sec}s. Exiting scheduler loop.")
                    break
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user.")


if __name__ == "__main__":
    scheduler = LocalScheduler()
    scheduler.start(run_immediately=False)

