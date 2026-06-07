"""MCP tool handlers for the GeneratorAgent.

Persists generated test cases to a ``test_cases`` table and to disk under
``cases/{operator_name}_cases.json``.
"""

from __future__ import annotations

import json
import logging
import random
import sqlite3
import time
from pathlib import Path
from typing import Any

from mcp_server.db import get_db

logger = logging.getLogger(__name__)

CASES_DIR_NAME = "cases"

# ── Retry policy for transient SQLite lock errors ─────────────────────────
# busy_timeout in db.py already lets SQLite wait up to 30s for the lock, but
# we still wrap the write in a small retry loop to absorb:
#   - the brief window where the WAL has been written but the holder hasn't
#     committed yet (older SQLite versions raised SQLITE_BUSY_LOCKED here)
#   - "database is locked" from non-SQLite sources (e.g. fsync on Windows)
#   - very long contention during a long-running LLM call that is mid-write
_MAX_INSERT_RETRIES = 5
_BASE_RETRY_DELAY_S = 0.1  # 100ms → 200ms → 400ms → 800ms → 1.6s (cap)


# ── Schema migration (idempotent) ────────────────────────────────────────────

def ensure_test_cases_schema() -> None:
    """Create ``test_cases`` table if it does not exist. Safe to call repeatedly."""
    conn = get_db().conn
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS test_cases (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                operator_name  TEXT NOT NULL,
                cases_json     TEXT NOT NULL,
                source         TEXT NOT NULL DEFAULT 'generated',
                created_at     TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_test_cases_operator
                ON test_cases(operator_name);
            """
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.warning("ensure_test_cases_schema: %s", e)


# ── Tool handlers ────────────────────────────────────────────────────────────

def do_save_test_cases(
    operator_name: str,
    cases_json: str,
    *,
    source: str = "generated",
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Persist ``cases_json`` to DB and ``cases/{operator_name}_cases.json`` on disk.

    Args:
        operator_name: Operator name (e.g. ``aclnnAdaLayerNorm``).
        cases_json: JSON-serialized list of test case records.
        source: Provenance label (e.g. ``"generated"``, ``"manual"``).
        output_dir: Override for the cases directory.  ``None`` → ``cases/``
            under the project root.

    Returns:
        Dict with ``saved_count`` and absolute ``output_path``.
    """
    ensure_test_cases_schema()

    # Validate that cases_json parses as a list.
    try:
        cases_list = json.loads(cases_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"cases_json is not valid JSON: {e}") from e
    if not isinstance(cases_list, list):
        raise ValueError("cases_json must deserialize to a list of test case records")

    # Persist to DB.  Write goes through a short retry loop because the
    # SQLite file is shared with the main agent process; even with
    # busy_timeout set on the connection (see mcp_server/db.py), a few
    # edge cases still surface as "database is locked" — most often on
    # Windows when an antivirus / fsync step holds the file briefly, or
    # when the WAL checkpoint runs in parallel with our write.
    _execute_with_retry(
        "INSERT INTO test_cases (operator_name, cases_json, source) VALUES (?, ?, ?)",
        (operator_name, cases_json, source),
    )

    # Persist to disk.
    out_path = _resolve_output_path(operator_name, output_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(cases_list, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(
        "Saved %d test cases for %s -> %s", len(cases_list), operator_name, out_path,
    )
    return {
        "operator_name": operator_name,
        "saved_count": len(cases_list),
        "output_path": str(out_path),
    }


def do_get_test_cases(operator_name: str) -> dict[str, Any] | None:
    """Return the most recent saved cases for ``operator_name``, or ``None``."""
    ensure_test_cases_schema()
    conn = get_db().conn
    row = conn.execute(
        "SELECT cases_json FROM test_cases "
        "WHERE operator_name = ? ORDER BY id DESC LIMIT 1",
        (operator_name,),
    ).fetchone()
    if row is None:
        return None
    return {
        "operator_name": operator_name,
        "cases": json.loads(row[0]),
    }


def do_list_test_case_operators() -> list[dict[str, Any]]:
    """Return all operator names that have saved cases, with counts."""
    ensure_test_cases_schema()
    conn = get_db().conn
    rows = conn.execute(
        "SELECT operator_name, COUNT(*) AS n, MAX(created_at) AS last_at "
        "FROM test_cases GROUP BY operator_name ORDER BY last_at DESC"
    ).fetchall()
    return [
        {"operator_name": r[0], "count": r[1], "last_created_at": r[2]}
        for r in rows
    ]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_output_path(operator_name: str, output_dir: str | None) -> Path:
    """Return the absolute Path to write the cases JSON to.

    Default layout (when ``output_dir`` is ``None``)::

        <operator-agent>/cases/<operator_name>_cases.json

    where ``<operator-agent>`` is the project root containing the
    ``packages/`` and ``data/`` directories.
    """
    if output_dir:
        base = Path(output_dir)
    else:
        # Project root = parents[5] of this file:
        #   mcp_server/tools/test_case_tools.py
        #   mcp_server/tools/        -> parents[0]
        #   mcp_server/              -> parents[1]
        #   mcp-server/src/          -> parents[2]
        #   mcp-server/              -> parents[3]
        #   packages/                -> parents[4]
        #   operator-agent/          -> parents[5]  ← project root
        base = Path(__file__).resolve().parents[5] / CASES_DIR_NAME
    return base / f"{operator_name}_cases.json"


def _is_transient_lock_error(exc: BaseException) -> bool:
    """Return True if the SQLite exception is a transient lock we should retry."""
    if isinstance(exc, sqlite3.OperationalError):
        msg = str(exc).lower()
        # Common phrasings across Python versions and SQLite builds:
        #   "database is locked"
        #   "database table is locked"
        #   "lock timeout"  (from busy_timeout overflow)
        return ("locked" in msg) or ("lock timeout" in msg)
    return False


def _execute_with_retry(sql: str, params: tuple) -> None:
    """Run ``sql`` with ``params`` and commit, retrying transient lock errors.

    The retry budget is intentionally small (max ~3.1s total) — combined with
    the 30s ``busy_timeout`` set on the connection, by the time we land here
    SQLite has *already* waited a long time for the lock.  These retries
    cover the last mile: cases where the lock was released and re-acquired
    by another writer before we could re-issue the statement.
    """
    conn = get_db().conn
    last_exc: BaseException | None = None
    for attempt in range(_MAX_INSERT_RETRIES):
        try:
            conn.execute(sql, params)
            conn.commit()
            if attempt > 0:
                logger.info(
                    "save_test_cases: insert succeeded on retry #%d", attempt,
                )
            return
        except Exception as exc:
            if not _is_transient_lock_error(exc):
                # Real error (NOT NULL, FK, etc.) — don't retry.
                raise
            last_exc = exc
            # Rollback any partial state from this failed attempt so the
            # next retry starts clean.
            try:
                conn.rollback()
            except sqlite3.OperationalError:
                pass
            if attempt == _MAX_INSERT_RETRIES - 1:
                break
            # Exponential backoff with jitter to avoid lock-step retries
            # when many requests pile up against the same lock holder.
            delay = min(_BASE_RETRY_DELAY_S * (2 ** attempt), 1.6)
            delay += random.uniform(0, _BASE_RETRY_DELAY_S)
            logger.warning(
                "save_test_cases: %s (attempt %d/%d), retrying in %.2fs",
                exc, attempt + 1, _MAX_INSERT_RETRIES, delay,
            )
            time.sleep(delay)
    # All retries exhausted.
    assert last_exc is not None
    raise last_exc
