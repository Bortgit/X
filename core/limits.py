"""Limites de ritmo, tope de preguntas e interruptor de apagado."""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

from core import db
from core.config import Settings, settings as default_settings


@dataclass(frozen=True)
class LimitCheck:
    allowed: bool
    reason: str | None = None  # "rate_limit" | "daily_global" | "question_cap" | "shutdown"


def is_shutdown_active(cfg: Settings | None = None) -> bool:
    cfg = cfg or default_settings
    if os.getenv(cfg.shutdown_env_var, "").strip().lower() in ("1", "true", "on", "si", "sí"):
        return True
    return cfg.shutdown_file.exists()


def check_rate_limit(conn: sqlite3.Connection, user_id: str, cfg: Settings | None = None) -> LimitCheck:
    cfg = cfg or default_settings
    count = db.count_recent_messages(conn, user_id, window_seconds=60)
    if count >= cfg.rate_limit_per_minute:
        return LimitCheck(False, "rate_limit")
    return LimitCheck(True)


def check_daily_global_limit(conn: sqlite3.Connection, cfg: Settings | None = None) -> LimitCheck:
    cfg = cfg or default_settings
    count = db.count_recent_global(conn, window_seconds=24 * 3600)
    if count >= cfg.daily_global_limit:
        return LimitCheck(False, "daily_global")
    return LimitCheck(True)


def check_question_cap(
    conn: sqlite3.Connection, user_id: str, story_hash: str, cfg: Settings | None = None
) -> LimitCheck:
    cfg = cfg or default_settings
    row = db.get_or_create_progress(conn, user_id, story_hash)
    if row["questions_asked"] >= cfg.max_questions_per_story:
        return LimitCheck(False, "question_cap")
    return LimitCheck(True)
