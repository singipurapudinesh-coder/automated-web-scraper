import os
from celery import Celery
from celery.schedules import crontab
import config

app = Celery("automated_web_scraper")

app.conf.update(
    broker_url=config.CELERY_BROKER_URL,
    result_backend=config.CELERY_RESULT_BACKEND,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,  # Recycles worker processes to prevent memory leaks from browser automation
)

# Automatically register tasks module
app.autodiscover_tasks(["tasks"])

# Celery Beat schedule configuration
app.conf.beat_schedule = {
    "run-scheduled-jobs-every-15-minutes": {
        "task": "tasks.celery_tasks.schedule_all_active_jobs_task",
        "schedule": 900.0,  # Every 15 minutes
    },
}

if __name__ == "__main__":
    app.start()

