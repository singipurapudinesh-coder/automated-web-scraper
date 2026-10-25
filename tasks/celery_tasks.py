import logging
import traceback
from typing import Any, Dict, Optional
from celery import shared_task

import database
from core.scrapers import get_scraper
import exporter

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_job_task(self, job_id: int) -> Dict[str, Any]:
    """Celery task to execute a dynamic scraping job and persist results to SQLite."""
    database.init_db()
    job = database.get_job(job_id)
    if not job:
        msg = f"Job ID {job_id} not found."
        logger.error(msg)
        return {"status": "error", "message": msg}

    if not job.get("enabled", 1):
        msg = f"Job '{job['name']}' (ID: {job_id}) is disabled. Skipping."
        logger.info(msg)
        return {"status": "skipped", "message": msg}

    logger.info(f"Starting scrape job '{job['name']}' (ID: {job_id}) -> {job['url']}")
    run_id = database.record_run_start(job_id)

    try:
        scraper = get_scraper(job["scraper_type"])
        items = scraper.scrape(job["url"], config=job["config"])
        saved_count = database.save_scraped_items(job_id, run_id, items)
        database.record_run_finish(run_id, status="success", items_count=saved_count)

        logger.info(
            f"Successfully finished job '{job['name']}' (ID: {job_id}): {saved_count} items stored."
        )
        return {
            "status": "success",
            "job_id": job_id,
            "run_id": run_id,
            "items_count": saved_count,
        }

    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}"
        logger.error(f"Error executing job {job_id}: {err_msg}")
        database.record_run_finish(run_id, status="failed", items_count=0, error_message=err_msg)

        # Retry transient network / driver errors
        try:
            self.retry(exc=exc)
        except Exception:
            pass

        return {
            "status": "failed",
            "job_id": job_id,
            "run_id": run_id,
            "error": str(exc),
        }


@shared_task
def schedule_all_active_jobs_task() -> Dict[str, Any]:
    """Celery Beat periodic task that inspects active jobs and dispatches execution tasks."""
    database.init_db()
    jobs = database.list_jobs(enabled_only=True)
    dispatched = []

    for job in jobs:
        # Queue task asynchronously
        res = execute_job_task.delay(job["id"])
        dispatched.append({"job_id": job["id"], "name": job["name"], "task_id": str(res.id)})

    return {"status": "dispatched", "total": len(dispatched), "jobs": dispatched}


@shared_task
def export_job_data_task(job_id: Optional[int] = None, file_format: str = "csv") -> str:
    """Asynchronously exports scraped data to CSV or JSON."""
    database.init_db()
    if file_format.lower() == "json":
        return exporter.export_to_json(job_id=job_id)
    return exporter.export_to_csv(job_id=job_id)

