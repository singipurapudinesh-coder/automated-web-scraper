import json
import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional
from config import DATABASE_PATH


@contextmanager
def get_connection(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """Yields a SQLite connection with row factory enabled, closing it upon exit."""
    path = db_path or DATABASE_PATH
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes the database schema if tables do not already exist."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Jobs Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL,
                scraper_type TEXT NOT NULL,
                schedule_interval_minutes INTEGER NOT NULL DEFAULT 60,
                enabled INTEGER NOT NULL DEFAULT 1,
                config_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Scrape Runs History Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scrape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                status TEXT NOT NULL, -- 'running', 'success', 'failed'
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                items_scraped INTEGER DEFAULT 0,
                error_message TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE
            );
            """
        )

        # Scraped Items Table (stores unstructured or semi-structured data as JSON)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scraped_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                run_id INTEGER,
                item_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
                FOREIGN KEY (run_id) REFERENCES scrape_runs (id) ON DELETE SET NULL,
                UNIQUE (job_id, item_hash) ON CONFLICT REPLACE
            );
            """
        )

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_job ON scraped_items (job_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_job ON scrape_runs (job_id);")
        conn.commit()


def compute_item_hash(item: Dict[str, Any]) -> str:
    """Generates a stable deterministic SHA-256 hash for an item dictionary."""
    normalized_json = json.dumps(item, sort_keys=True, default=str)
    return hashlib.sha256(normalized_json.encode("utf-8")).hexdigest()


def add_or_update_job(
    name: str,
    url: str,
    scraper_type: str,
    schedule_interval_minutes: int = 60,
    enabled: bool = True,
    config: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None,
) -> int:
    """Adds a new scrape job or updates an existing one."""
    config_str = json.dumps(config or {})
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (name, url, scraper_type, schedule_interval_minutes, enabled, config_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                url = excluded.url,
                scraper_type = excluded.scraper_type,
                schedule_interval_minutes = excluded.schedule_interval_minutes,
                enabled = excluded.enabled,
                config_json = excluded.config_json,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
            """,
            (name, url, scraper_type, schedule_interval_minutes, 1 if enabled else 0, config_str),
        )
        row = cursor.fetchone()
        conn.commit()
        return row["id"]


def get_job(identifier: Any, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetches a job by numeric ID or by name."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            cursor.execute("SELECT * FROM jobs WHERE id = ?;", (int(identifier),))
        else:
            cursor.execute("SELECT * FROM jobs WHERE name = ?;", (str(identifier),))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["config"] = json.loads(res.get("config_json") or "{}")
        return res


def list_jobs(enabled_only: bool = False, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns a list of all registered scraping jobs."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM jobs"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY id ASC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        jobs = []
        for r in rows:
            d = dict(r)
            d["config"] = json.loads(d.get("config_json") or "{}")
            jobs.append(d)
        return jobs


def delete_job(identifier: Any, db_path: Optional[str] = None) -> bool:
    """Deletes a job and associated runs/items (cascaded)."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            cursor.execute("DELETE FROM jobs WHERE id = ?;", (int(identifier),))
        else:
            cursor.execute("DELETE FROM jobs WHERE name = ?;", (str(identifier),))
        conn.commit()
        return cursor.rowcount > 0


def record_run_start(job_id: int, db_path: Optional[str] = None) -> int:
    """Records the beginning of a scrape run."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO scrape_runs (job_id, status, start_time)
            VALUES (?, 'running', CURRENT_TIMESTAMP)
            RETURNING id;
            """,
            (job_id,),
        )
        row = cursor.fetchone()
        conn.commit()
        return row["id"]


def record_run_finish(
    run_id: int,
    status: str,
    items_count: int,
    error_message: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    """Updates a scrape run record upon completion or failure."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE scrape_runs
            SET status = ?,
                end_time = CURRENT_TIMESTAMP,
                items_scraped = ?,
                error_message = ?
            WHERE id = ?;
            """,
            (status, items_count, error_message, run_id),
        )
        conn.commit()


def save_scraped_items(
    job_id: int,
    run_id: Optional[int],
    items: List[Dict[str, Any]],
    db_path: Optional[str] = None,
) -> int:
    """Saves or updates scraped items into the database with deduplication."""
    if not items:
        return 0

    inserted_or_updated = 0
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        for item in items:
            item_hash = compute_item_hash(item)
            payload_str = json.dumps(item)
            cursor.execute(
                """
                INSERT INTO scraped_items (job_id, run_id, item_hash, payload_json, scraped_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(job_id, item_hash) DO UPDATE SET
                    run_id = excluded.run_id,
                    payload_json = excluded.payload_json,
                    scraped_at = CURRENT_TIMESTAMP;
                """,
                (job_id, run_id, item_hash, payload_str),
            )
            inserted_or_updated += 1
        conn.commit()
    return inserted_or_updated


def get_scraped_items(
    job_id: Optional[int] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieves scraped items, unpacking JSON payloads into dictionaries."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT id, job_id, run_id, item_hash, payload_json, scraped_at FROM scraped_items"
        params: List[Any] = []
        if job_id is not None:
            query += " WHERE job_id = ?"
            params.append(job_id)
        query += " ORDER BY scraped_at DESC"
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        results = []
        for r in rows:
            data = json.loads(r["payload_json"])
            results.append({
                "item_id": r["id"],
                "job_id": r["job_id"],
                "run_id": r["run_id"],
                "scraped_at": r["scraped_at"],
                "item_hash": r["item_hash"],
                **data,
            })
        return results


def get_job_stats(job_id: Optional[int] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Computes summary statistics for a specific job or all jobs."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        items_filter = "WHERE job_id = ?" if job_id is not None else ""
        runs_filter = "WHERE job_id = ?" if job_id is not None else ""
        params = (job_id,) if job_id is not None else ()

        cursor.execute(f"SELECT COUNT(*) as total_items FROM scraped_items {items_filter};", params)
        total_items = cursor.fetchone()["total_items"]

        cursor.execute(f"SELECT COUNT(*) as total_runs FROM scrape_runs {runs_filter};", params)
        total_runs = cursor.fetchone()["total_runs"]

        cursor.execute(
            f"SELECT COUNT(*) as success_runs FROM scrape_runs {runs_filter} {'AND' if runs_filter else 'WHERE'} status = 'success';",
            params,
        )
        success_runs = cursor.fetchone()["success_runs"]

        cursor.execute(
            f"SELECT * FROM scrape_runs {runs_filter} ORDER BY id DESC LIMIT 1;",
            params,
        )
        last_run_row = cursor.fetchone()
        last_run = dict(last_run_row) if last_run_row else None

        return {
            "total_items": total_items,
            "total_runs": total_runs,
            "successful_runs": success_runs,
            "failed_runs": total_runs - success_runs,
            "last_run": last_run,
        }
