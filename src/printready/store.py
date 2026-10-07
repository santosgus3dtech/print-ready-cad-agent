import json
import os
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def data_root() -> Path:
    path = Path(os.getenv("PRINTREADY_DATA_DIR", ROOT / "_data")).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def job_directory(job_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise ValueError("Invalid job identifier.")
    return data_root() / "jobs" / job_id


def connection():
    database = sqlite3.connect(data_root() / "jobs.sqlite3", timeout=30)
    database.execute("PRAGMA journal_mode=WAL")
    database.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, created_at TEXT, payload TEXT)")
    return database


def save_job(job: dict):
    with connection() as db:
        db.execute(
            "INSERT INTO jobs VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
            (job["id"], job["created_at"], json.dumps(job)),
        )


def get_job(job_id: str) -> dict | None:
    job_directory(job_id)
    with connection() as db:
        row = db.execute("SELECT payload FROM jobs WHERE id=?", (job_id,)).fetchone()
    return json.loads(row[0]) if row else None


def recent_jobs() -> list[dict]:
    with connection() as db:
        rows = db.execute("SELECT payload FROM jobs ORDER BY created_at DESC LIMIT 30").fetchall()
    return [json.loads(row[0]) for row in rows]
