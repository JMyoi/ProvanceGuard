"""Structured audit log backed by SQLite.

Every attribution decision and every appeal is recorded as a row in `audit_log`.
Classification rows carry the full decision (both signal scores, combined
confidence, attribution, status); appeal rows link back to the same content_id
and carry the creator's reasoning. This is the canonical record graders read via
GET /log, and the store the appeal endpoint updates.
"""

import sqlite3
from datetime import datetime, timezone

from config import DB_PATH


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the audit_log table if it doesn't exist. Safe to call repeatedly."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id         TEXT    NOT NULL,
                creator_id         TEXT,
                timestamp          TEXT    NOT NULL,
                event_type         TEXT    NOT NULL,  -- 'classification' | 'appeal'
                attribution        TEXT,              -- likely_ai | uncertain | likely_human
                confidence         REAL,              -- combined P(AI), 0-1
                llm_score          REAL,              -- signal 1
                stylometric_score  REAL,              -- signal 2 (added in M4)
                status             TEXT,              -- classified | under_review
                appeal_reasoning   TEXT               -- populated on appeal rows
            )
            """
        )


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def log_classification(
    content_id,
    creator_id,
    attribution,
    confidence,
    llm_score,
    stylometric_score=None,
    status="classified",
):
    """Write one classification decision to the audit log."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO audit_log
                (content_id, creator_id, timestamp, event_type,
                 attribution, confidence, llm_score, stylometric_score, status)
            VALUES (?, ?, ?, 'classification', ?, ?, ?, ?, ?)
            """,
            (
                content_id,
                creator_id,
                _now_iso(),
                attribution,
                confidence,
                llm_score,
                stylometric_score,
                status,
            ),
        )


def get_latest_classification(content_id):
    """Return the most recent classification row for a content_id, or None."""
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM audit_log
            WHERE content_id = ? AND event_type = 'classification'
            ORDER BY id DESC LIMIT 1
            """,
            (content_id,),
        ).fetchone()
    return dict(row) if row else None


def log_appeal(content_id, creator_id, creator_reasoning, original):
    """Record an appeal row and flip the original classification's status.

    `original` is the classification row dict (from get_latest_classification)
    so the appeal entry preserves the contested attribution/confidence beside
    the creator's reasoning.
    """
    with _connect() as conn:
        # Mark the original decision as under review.
        conn.execute(
            "UPDATE audit_log SET status = 'under_review' WHERE content_id = ? AND event_type = 'classification'",
            (content_id,),
        )
        # Add the appeal event.
        conn.execute(
            """
            INSERT INTO audit_log
                (content_id, creator_id, timestamp, event_type,
                 attribution, confidence, llm_score, stylometric_score,
                 status, appeal_reasoning)
            VALUES (?, ?, ?, 'appeal', ?, ?, ?, ?, 'under_review', ?)
            """,
            (
                content_id,
                creator_id or original.get("creator_id"),
                _now_iso(),
                original.get("attribution"),
                original.get("confidence"),
                original.get("llm_score"),
                original.get("stylometric_score"),
                creator_reasoning,
            ),
        )


def get_log(limit=50):
    """Return the most recent audit entries (newest first) as a list of dicts."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
