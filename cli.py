import json
import os
import sys
from pathlib import Path
from typing import Optional
import click
from tabulate import tabulate

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import database
import exporter
from core.scrapers import SCRAPER_REGISTRY
from scheduler import LocalScheduler, run_job_sync


@click.group()
def main():
    """Automated Dynamic Web Scraper with Celery and SQLite."""
    database.init_db()


@main.command("init")
def init():
    """Initializes the SQLite database and seeds default sample jobs."""
    database.init_db()

    # Seed sample dynamic quotes job
    job1_id = database.add_or_update_job(
        name="quotes_sample",
        url="https://quotes.toscrape.com/js/",
        scraper_type="quotes",
        schedule_interval_minutes=30,
        enabled=True,
        config={"wait_selector": ".quote", "scroll_down": False},
    )

    # Seed sample dynamic ecommerce books job
    job2_id = database.add_or_update_job(
        name="books_sample",
        url="https://books.toscrape.com/",
        scraper_type="ecommerce",
        schedule_interval_minutes=60,
        enabled=True,
        config={"scroll_down": True},
    )

    click.echo(click.style("Database initialized successfully!", fg="green"))
    click.echo(f"  * Seeded 'quotes_sample' (Job ID: {job1_id})")
    click.echo(f"  * Seeded 'books_sample' (Job ID: {job2_id})")


@main.command("list-jobs")
@click.option("--all", "show_all", is_flag=True, help="Include disabled jobs")
def list_jobs(show_all: bool):
    """Lists all configured scraping jobs."""
    jobs = database.list_jobs(enabled_only=not show_all)
    if not jobs:
        click.echo("No jobs found. Run 'python cli.py init' to seed default jobs.")
        return

    table_data = []
    for j in jobs:
        stats = database.get_job_stats(j["id"])
        last_run = stats["last_run"]
        last_status = last_run["status"] if last_run else "never run"
        table_data.append([
            j["id"],
            j["name"],
            j["scraper_type"],
            f"Every {j['schedule_interval_minutes']}m",
            "Yes" if j["enabled"] else "No",
            stats["total_items"],
            last_status,
            j["url"][:35] + ("..." if len(j["url"]) > 35 else ""),
        ])

    headers = ["ID", "Name", "Type", "Schedule", "Enabled", "Items", "Last Run", "URL"]
    click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))


@main.command("add-job")
@click.option("--name", required=True, help="Unique identifier for the job")
@click.option("--url", required=True, help="Target website URL")
@click.option(
    "--type",
    "scraper_type",
    type=click.Choice(list(SCRAPER_REGISTRY.keys())),
    default="dynamic_generic",
    help="Scraper type",
)
@click.option("--interval", default=60, help="Schedule interval in minutes")
@click.option("--config-file", type=click.Path(exists=True), help="Path to JSON configuration file")
@click.option("--config-json", help="Inline JSON string for selectors and options")
def add_job(name: str, url: str, scraper_type: str, interval: int, config_file: Optional[str], config_json: Optional[str]):
    """Registers a new scraping job or updates an existing one."""
    cfg = {}
    if config_file:
        with open(config_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    elif config_json:
        cfg = json.loads(config_json)

    job_id = database.add_or_update_job(
        name=name,
        url=url,
        scraper_type=scraper_type,
        schedule_interval_minutes=interval,
        enabled=True,
        config=cfg,
    )
    click.echo(click.style(f"Job '{name}' saved successfully with ID: {job_id}!", fg="green"))


@main.command("run")
@click.argument("job_identifier")
@click.option("--celery", "use_celery", is_flag=True, help="Dispatch as asynchronous Celery task")
def run_job(job_identifier: str, use_celery: bool):
    """Executes a scraping job immediately (by ID or name)."""
    job = database.get_job(job_identifier)
    if not job:
        click.echo(click.style(f"Error: Job '{job_identifier}' not found.", fg="red"))
        sys.exit(1)

    if use_celery:
        from tasks.celery_tasks import execute_job_task
        task = execute_job_task.delay(job["id"])
        click.echo(click.style(f"Dispatched Celery task ID: {task.id} for job '{job['name']}'", fg="cyan"))
    else:
        click.echo(click.style(f"Running job '{job['name']}' synchronously...", fg="cyan"))
        run_job_sync(job["id"])


@main.command("export")
@click.option("--job", "job_identifier", default=None, help="Job ID or name to export (default: all jobs)")
@click.option("--format", "file_format", type=click.Choice(["csv", "json"]), default="csv", help="Export file format")
@click.option("--output", "output_path", default=None, help="Destination file path")
def export_data(job_identifier: Optional[str], file_format: str, output_path: Optional[str]):
    """Exports scraped data from SQLite to a CSV or JSON file."""
    job_id = None
    if job_identifier:
        job = database.get_job(job_identifier)
        if not job:
            click.echo(click.style(f"Error: Job '{job_identifier}' not found.", fg="red"))
            sys.exit(1)
        job_id = job["id"]

    try:
        if file_format == "csv":
            path = exporter.export_to_csv(job_id=job_id, output_path=output_path)
        else:
            path = exporter.export_to_json(job_id=job_id, output_path=output_path)

        click.echo(click.style(f"Data exported successfully to: {path}", fg="green"))
    except ValueError as e:
        click.echo(click.style(f"Export warning: {e}", fg="yellow"))


@main.command("view-data")
@click.option("--job", "job_identifier", default=None, help="Job ID or name to filter by")
@click.option("--limit", default=10, help="Number of rows to display")
def view_data(job_identifier: Optional[str], limit: int):
    """Displays recently scraped items in a terminal table."""
    job_id = None
    if job_identifier:
        job = database.get_job(job_identifier)
        if not job:
            click.echo(click.style(f"Error: Job '{job_identifier}' not found.", fg="red"))
            sys.exit(1)
        job_id = job["id"]

    items = database.get_scraped_items(job_id=job_id, limit=limit)
    if not items:
        click.echo("No data found in SQLite database.")
        return

    # Clean display fields
    display_rows = []
    for it in items:
        row = {
            "ID": it.get("item_id"),
            "Job ID": it.get("job_id"),
            "Scraped At": it.get("scraped_at"),
            "Preview": str({k: v for k, v in it.items() if k not in ("item_id", "job_id", "run_id", "item_hash", "scraped_at")})[:80] + "...",
        }
        display_rows.append(row)

    click.echo(tabulate(display_rows, headers="keys", tablefmt="grid"))


@main.command("stats")
@click.option("--job", "job_identifier", default=None, help="Job ID or name to inspect")
def show_stats(job_identifier: Optional[str]):
    """Displays summary metrics and execution logs."""
    job_id = None
    title = "All Scraping Jobs"
    if job_identifier:
        job = database.get_job(job_identifier)
        if not job:
            click.echo(click.style(f"Error: Job '{job_identifier}' not found.", fg="red"))
            sys.exit(1)
        job_id = job["id"]
        title = f"Job: {job['name']} (ID: {job_id})"

    stats = database.get_job_stats(job_id)
    click.echo(click.style(f"\n--- Statistics for {title} ---", fg="cyan", bold=True))
    click.echo(f"  * Total Unique Items Stored : {stats['total_items']}")
    click.echo(f"  * Total Scrape Runs         : {stats['total_runs']}")
    click.echo(f"  * Successful Runs           : {stats['successful_runs']}")
    click.echo(f"  * Failed Runs               : {stats['failed_runs']}")

    if stats["last_run"]:
        lr = stats["last_run"]
        click.echo(f"  * Last Run Status           : {lr['status']}")
        click.echo(f"  * Last Run Start Time       : {lr['start_time']}")
        click.echo(f"  * Last Run End Time         : {lr['end_time']}")
        click.echo(f"  * Items Scraped in Last Run : {lr['items_scraped']}")
        if lr.get("error_message"):
            click.echo(click.style(f"  * Last Error                : {lr['error_message'][:150]}...", fg="red"))
    click.echo("")


@main.command("schedule")
@click.option("--run-now", is_flag=True, help="Trigger all active jobs immediately before waiting")
@click.option("--duration", type=int, default=None, help="Stop scheduler after N seconds (useful for testing/verification)")
def start_scheduler(run_now: bool, duration: Optional[int]):
    """Starts the standalone periodic scheduler loop."""
    scheduler = LocalScheduler()
    scheduler.start(run_immediately=run_now, max_duration_sec=duration)


@main.command("worker")
@click.option("--concurrency", default=1, help="Worker concurrency")
def start_worker(concurrency: int):
    """Starts a Celery worker configured for Windows compatibility."""
    import subprocess
    cmd = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "celery_app.app",
        "worker",
        "--loglevel=info",
        "--pool=solo" if os.name == "nt" else "--pool=prefork",
        f"--concurrency={concurrency}",
    ]
    click.echo(f"Launching Celery worker: {' '.join(cmd)}")
    subprocess.run(cmd)


@main.command("beat")
def start_beat():
    """Starts the Celery Beat periodic task dispatcher."""
    import subprocess
    cmd = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "celery_app.app",
        "beat",
        "--loglevel=info",
    ]
    click.echo(f"Launching Celery beat: {' '.join(cmd)}")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
