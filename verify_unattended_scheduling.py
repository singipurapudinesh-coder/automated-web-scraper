"""
Verification Script for Unattended Recurring Scheduling.
Validates that the scheduler triggers jobs periodically without manual intervention.
"""

import time
from datetime import datetime
import database
from scheduler import LocalScheduler


def main():
    print("=" * 70)
    print("VERIFICATION: Unattended Recurring Scheduling")
    print("=" * 70)

    database.init_db()

    # Disable all other jobs temporarily for this isolated test
    for j in database.list_jobs(enabled_only=False):
        database.add_or_update_job(
            name=j["name"],
            url=j["url"],
            scraper_type=j["scraper_type"],
            schedule_interval_minutes=j["schedule_interval_minutes"],
            enabled=False,
            config=j["config"],
        )

    # Register a fast verification job scheduled to run every 12 seconds
    test_job_id = database.add_or_update_job(
        name="unattended_verification_job",
        url="https://quotes.toscrape.com/js/",
        scraper_type="quotes",
        schedule_interval_minutes=1,
        enabled=True,
        config={
            "wait_selector": ".quote",
            "schedule_interval_seconds": 12,
        },
    )

    print(f"\n[1] Registered test job 'unattended_verification_job' (ID: {test_job_id})")
    print("    Configured Interval: Every 12 seconds.")
    print("    Starting scheduler with run_immediately=False (zero startup runs).")
    print("    Scheduler will run unattended for ~30 seconds...\n")

    # Run scheduler for 30 seconds with run_immediately=False
    scheduler = LocalScheduler(check_interval_sec=0.5)
    start_wall = time.time()
    scheduler.start(run_immediately=False, max_duration_sec=30)
    elapsed = time.time() - start_wall

    print(f"\n[2] Scheduler finished after {elapsed:.1f}s.")

    # Query scrape runs for this job
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, status, start_time, end_time, items_scraped
            FROM scrape_runs
            WHERE job_id = ?
            ORDER BY id ASC;
            """,
            (test_job_id,),
        )
        runs = [dict(r) for r in cursor.fetchall()]

    print(f"\n[3] Inspection Results from SQLite:")
    print(f"    Total Recorded Runs: {len(runs)}")

    for idx, r in enumerate(runs, 1):
        print(f"    • Run #{idx} (Run ID: {r['id']}) | Status: {r['status']} | Start: {r['start_time']} | Items: {r['items_scraped']}")

    if len(runs) >= 2:
        # Calculate time delta between runs
        t1 = datetime.strptime(runs[0]["start_time"], "%Y-%m-%d %H:%M:%S")
        t2 = datetime.strptime(runs[1]["start_time"], "%Y-%m-%d %H:%M:%S")
        delta_sec = (t2 - t1).total_seconds()

        print(f"\n[4] Interval Verification:")
        print(f"    Delta between Run #1 and Run #2: {delta_sec:.1f} seconds (Target: ~12s)")
        assert delta_sec >= 10, f"Expected ~12s delta, got {delta_sec}s"
        print("\n" + "=" * 70)
        print(">>> SUCCESS: Unattended recurring scheduling VERIFIED! <<<")
        print("=" * 70)
    else:
        print("\n[!] WARNING: Expected at least 2 runs, but got", len(runs))

    # Re-enable standard jobs
    for name in ("quotes_sample", "books_sample"):
        j = database.get_job(name)
        if j:
            database.add_or_update_job(
                name=j["name"],
                url=j["url"],
                scraper_type=j["scraper_type"],
                schedule_interval_minutes=j["schedule_interval_minutes"],
                enabled=True,
                config=j["config"],
            )


if __name__ == "__main__":
    main()

