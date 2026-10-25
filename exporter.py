import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

import config
import database


def _flatten_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Flattens nested structures (e.g., lists or dicts) for tabular CSV export."""
    flattened = {}
    for k, v in item.items():
        if isinstance(v, list):
            # Join list of primitives or dump complex lists to JSON string
            if all(isinstance(x, (str, int, float, bool)) for x in v):
                flattened[k] = ", ".join(str(x) for x in v)
            else:
                flattened[k] = json.dumps(v)
        elif isinstance(v, dict):
            flattened[k] = json.dumps(v)
        else:
            flattened[k] = v
    return flattened


def export_to_csv(
    job_id: Optional[int] = None,
    output_path: Optional[str] = None,
    db_path: Optional[str] = None,
) -> str:
    """Exports scraped items from SQLite to a CSV file."""
    items = database.get_scraped_items(job_id=job_id, db_path=db_path)
    if not items:
        raise ValueError(f"No data available to export for job_id={job_id}")

    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"job_{job_id}" if job_id is not None else "all_jobs"
        output_file = config.EXPORTS_DIR / f"{prefix}_{timestamp}.csv"
    else:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

    flattened_items = [_flatten_item(it) for it in items]
    df = pd.DataFrame(flattened_items)
    df.to_csv(output_file, index=False, encoding="utf-8")
    return str(output_file.resolve())


def export_to_json(
    job_id: Optional[int] = None,
    output_path: Optional[str] = None,
    indent: int = 2,
    db_path: Optional[str] = None,
) -> str:
    """Exports scraped items from SQLite to a formatted JSON file."""
    items = database.get_scraped_items(job_id=job_id, db_path=db_path)
    if not items:
        raise ValueError(f"No data available to export for job_id={job_id}")

    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"job_{job_id}" if job_id is not None else "all_jobs"
        output_file = config.EXPORTS_DIR / f"{prefix}_{timestamp}.json"
    else:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=indent, default=str)

    return str(output_file.resolve())

