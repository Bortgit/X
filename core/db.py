"""Capa de persistencia en SQLite: mensajes procesados, progreso por jugador
y registro tecnico de cada interaccion."""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from core.config import Settings, settings as default_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_messages (
    message_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    ts REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS player_progress (
    user_id TEXT NOT NULL,
    story_hash TEXT NOT NULL,
    questions_asked INTEGER NOT NULL DEFAULT 0,
    won INTEGER NOT NULL DEFAULT 0,
    gave_up INTEGER NOT NULL DEFAULT 0,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    PRIMARY KEY (user_id, story_hash)
);

CREATE TABLE IF NOT EXISTS interaction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    user_id TEXT NOT NULL,
    message_id TEXT,
    story_hash TEXT,
    raw_text TEXT,
    category TEXT,
    response_text TEXT
);

CREATE INDEX IF NOT EXISTS idx_interaction_user_ts ON interaction_log(user_id, ts);
CREATE INDEX IF NOT EXISTS idx_processed_user_ts ON processed_messages(user_id, ts);
"""


def get_connection(cfg: Settings | None = None) -> sqlite3.Connection:
    cfg = cfg or default_settings
    if cfg.db_path == ":memory:":
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        return conn

    db_path = Path(cfg.db_path)
    if not db_path.is_absolute():
        db_path = cfg.project_root / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def connection_scope(cfg: Settings | None = None):
    conn = get_connection(cfg)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def is_duplicate_message(conn: sqlite3.Connection, message_id: str | None) -> bool:
    if not message_id:
        return False
    row = conn.execute(
        "SELECT 1 FROM processed_messages WHERE message_id = ?", (message_id,)
    ).fetchone()
    return row is not None


def mark_message_processed(
    conn: sqlite3.Connection, message_id: str | None, user_id: str
) -> None:
    if not message_id:
        return
    conn.execute(
        "INSERT OR IGNORE INTO processed_messages (message_id, user_id, ts) VALUES (?, ?, ?)",
        (message_id, user_id, time.time()),
    )


def get_or_create_progress(
    conn: sqlite3.Connection, user_id: str, story_hash: str
) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM player_progress WHERE user_id = ? AND story_hash = ?",
        (user_id, story_hash),
    ).fetchone()
    if row is not None:
        return row
    now = time.time()
    conn.execute(
        """INSERT INTO player_progress
           (user_id, story_hash, questions_asked, won, gave_up, first_seen, last_seen)
           VALUES (?, ?, 0, 0, 0, ?, ?)""",
        (user_id, story_hash, now, now),
    )
    return conn.execute(
        "SELECT * FROM player_progress WHERE user_id = ? AND story_hash = ?",
        (user_id, story_hash),
    ).fetchone()


def increment_questions(conn: sqlite3.Connection, user_id: str, story_hash: str) -> int:
    get_or_create_progress(conn, user_id, story_hash)
    conn.execute(
        """UPDATE player_progress SET questions_asked = questions_asked + 1,
           last_seen = ? WHERE user_id = ? AND story_hash = ?""",
        (time.time(), user_id, story_hash),
    )
    row = conn.execute(
        "SELECT questions_asked FROM player_progress WHERE user_id = ? AND story_hash = ?",
        (user_id, story_hash),
    ).fetchone()
    return row["questions_asked"]


def set_won(conn: sqlite3.Connection, user_id: str, story_hash: str) -> None:
    get_or_create_progress(conn, user_id, story_hash)
    conn.execute(
        "UPDATE player_progress SET won = 1, last_seen = ? WHERE user_id = ? AND story_hash = ?",
        (time.time(), user_id, story_hash),
    )


def set_gave_up(conn: sqlite3.Connection, user_id: str, story_hash: str) -> None:
    get_or_create_progress(conn, user_id, story_hash)
    conn.execute(
        "UPDATE player_progress SET gave_up = 1, last_seen = ? WHERE user_id = ? AND story_hash = ?",
        (time.time(), user_id, story_hash),
    )


def log_interaction(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    message_id: str | None,
    story_hash: str | None,
    raw_text: str,
    category: str,
    response_text: str | None,
) -> None:
    conn.execute(
        """INSERT INTO interaction_log
           (ts, user_id, message_id, story_hash, raw_text, category, response_text)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (time.time(), user_id, message_id, story_hash, raw_text, category, response_text),
    )


def count_recent_messages(conn: sqlite3.Connection, user_id: str, window_seconds: float) -> int:
    since = time.time() - window_seconds
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM processed_messages WHERE user_id = ? AND ts >= ?",
        (user_id, since),
    ).fetchone()
    return row["c"]


def count_recent_global(conn: sqlite3.Connection, window_seconds: float) -> int:
    since = time.time() - window_seconds
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM processed_messages WHERE ts >= ?", (since,)
    ).fetchone()
    return row["c"]
