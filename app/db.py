"""SQLite persistence layer (zero-infra alternative to Postgres/pgvector)."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    full_name TEXT,
    email TEXT,
    summary TEXT,
    parsed_json TEXT,          -- structured CV as JSON
    target_roles TEXT,         -- JSON array
    target_locations TEXT,     -- JSON array
    min_salary INTEGER,
    work_mode TEXT,
    profile_text TEXT,         -- flattened text used for matching
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,       -- source:external_id
    source TEXT,
    external_id TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    remote INTEGER,
    salary_min INTEGER,
    salary_max INTEGER,
    description TEXT,
    tags TEXT,                 -- JSON array
    apply_url TEXT,
    posted_at TEXT,
    ingested_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS matches (
    job_id TEXT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    score REAL,
    reasoning TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    job_id TEXT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'queued',
    cover_letter TEXT,
    notes TEXT,
    events TEXT DEFAULT '[]',  -- JSON array timeline
    applied_at TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);
"""


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    d = dict(row)
    for key in ("parsed_json", "target_roles", "target_locations", "tags", "events"):
        if key in d and isinstance(d[key], str) and d[key]:
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                pass
    return d
