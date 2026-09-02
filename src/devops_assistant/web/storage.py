"""
SQLite-based Run History Storage for Web Dashboard.
"""

import sqlite3
import json
import os
from typing import List, Optional
from devops_assistant.config import CIReportData


DB_PATH = os.path.join(os.path.dirname(__file__), "runs.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the runs table if it doesn't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                target_path TEXT,
                quality_score INTEGER,
                total_violations INTEGER,
                coverage_percentage REAL,
                overall_passed INTEGER,
                report_json TEXT NOT NULL
            )
        """)
        conn.commit()


def save_run(report: CIReportData):
    """Persist a CI report to the database."""
    init_db()
    with _get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO runs
            (run_id, timestamp, target_path, quality_score, total_violations,
             coverage_percentage, overall_passed, report_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report.run_id,
            report.timestamp,
            report.target_path,
            report.quality_score,
            len(report.violations),
            report.test_result.coverage_percentage,
            1 if report.overall_passed else 0,
            report.model_dump_json(),
        ))
        conn.commit()


def get_run(run_id: str) -> Optional[CIReportData]:
    """Retrieve a single run by ID."""
    init_db()
    with _get_conn() as conn:
        row = conn.execute("SELECT report_json FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row:
        return CIReportData.model_validate_json(row["report_json"])
    return None


def list_runs(limit: int = 50) -> List[dict]:
    """Return summary rows of all runs, newest first."""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT run_id, timestamp, target_path, quality_score,
                   total_violations, coverage_percentage, overall_passed
            FROM runs ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def delete_run(run_id: str):
    """Delete a run by ID."""
    init_db()
    with _get_conn() as conn:
        conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
        conn.commit()


def get_trend_data(limit: int = 20) -> List[dict]:
    """Return trend-friendly rows for charting (oldest first)."""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT run_id, timestamp, quality_score, total_violations, coverage_percentage
            FROM runs ORDER BY timestamp ASC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]
