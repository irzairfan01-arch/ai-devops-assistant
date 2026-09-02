"""
Metrics Trend Tracker.
Computes score deltas and coverage trends from run history.
"""

from typing import List, Optional
from devops_assistant.config import MetricsSummary


def compute_metrics(runs: List[dict]) -> List[MetricsSummary]:
    """
    Given a list of run summary dicts (from storage.list_runs),
    compute MetricsSummary with deltas vs previous run.
    """
    summaries = []
    for i, run in enumerate(runs):
        prev = runs[i - 1] if i > 0 else None
        summaries.append(MetricsSummary(
            run_id=run["run_id"],
            timestamp=run["timestamp"],
            quality_score=run["quality_score"],
            total_violations=run["total_violations"],
            coverage_percentage=run["coverage_percentage"],
            score_delta=(run["quality_score"] - prev["quality_score"]) if prev else None,
            violation_delta=(run["total_violations"] - prev["total_violations"]) if prev else None,
        ))
    return summaries


def get_latest_metrics() -> Optional[MetricsSummary]:
    """Get the MetricsSummary for the most recent run."""
    try:
        from devops_assistant.web.storage import list_runs
        runs = list_runs(limit=2)
        if not runs:
            return None
        summaries = compute_metrics(list(reversed(runs)))
        return summaries[-1] if summaries else None
    except Exception:
        return None
