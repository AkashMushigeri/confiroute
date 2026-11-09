"""Automated safety and operational alerts engine for ConfiRoute.

Monitors:
1. High human escalation rate over sliding window of N queries.
2. Clinician review backlog exceeding maximum capacity.
3. Repeated low-confidence predictions localized to specific medical subjects/topics.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import sqlite3

from confiroute.config import get_config
from confiroute.db.database import (
    get_connection,
    init_db,
    insert_alert,
    get_active_alerts,
    has_recent_alert_of_type,
    clear_alerts,
)


class AlertEngine:
    """Evaluates operational and safety alert conditions and records alerts in SQLite."""

    def __init__(self, custom_db_path: Optional[Path] = None):
        self.custom_db_path = custom_db_path
        self.config = get_config()
        self.alerts_cfg = getattr(self.config, "alerts_config", {
            "high_escalation_threshold": 0.50,
            "window_size": 20,
            "backlog_threshold": 10,
            "repeated_low_confidence_threshold": 3,
            "low_confidence_threshold": 0.50,
        })

    def check_high_escalation_rate(
        self,
        window_size: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Alert 1: Trigger when human escalation rate exceeds threshold over last N queries."""
        w_size = window_size or self.alerts_cfg.get("window_size", 20)
        thresh = threshold if threshold is not None else self.alerts_cfg.get("high_escalation_threshold", 0.50)

        conn = get_connection(self.custom_db_path)
        try:
            cursor = conn.execute(
                """
                SELECT route
                FROM routes
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (w_size,),
            )
            rows = cursor.fetchall()
            if len(rows) < 5:  # Need minimum sample size
                return None

            total = len(rows)
            human_count = sum(1 for r in rows if r["route"] == "human")
            escalation_rate = human_count / total

            if escalation_rate >= thresh:
                return {
                    "alert_type": "high_escalation_rate",
                    "severity": "critical" if escalation_rate >= 0.75 else "warning",
                    "message": (
                        f"High human escalation rate detected: {escalation_rate:.1%} "
                        f"({human_count}/{total} queries in recent window) exceeds threshold ({thresh:.1%})."
                    ),
                    "metric_value": round(escalation_rate, 4),
                }
            return None
        finally:
            conn.close()

    def check_review_backlog(
        self,
        threshold: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Alert 2: Trigger when pending human reviews exceed configured capacity."""
        thresh = threshold if threshold is not None else self.alerts_cfg.get("backlog_threshold", 10)

        conn = get_connection(self.custom_db_path)
        try:
            cursor = conn.execute(
                "SELECT count(*) as c FROM routes WHERE status IN ('pending_human', 'pending_tier2')"
            )
            backlog_count = cursor.fetchone()["c"]

            if backlog_count >= thresh:
                return {
                    "alert_type": "review_backlog",
                    "severity": "critical" if backlog_count >= (thresh * 2) else "warning",
                    "message": (
                        f"Clinician review backlog exceeds threshold: {backlog_count} pending cases "
                        f"(capacity limit: {thresh})."
                    ),
                    "metric_value": backlog_count,
                }
            return None
        finally:
            conn.close()

    def check_repeated_low_confidence(
        self,
        consecutive_limit: Optional[int] = None,
        low_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Alert 3: Trigger when multiple low-confidence predictions occur for the same subject."""
        c_limit = consecutive_limit or self.alerts_cfg.get("repeated_low_confidence_threshold", 3)
        low_t = low_threshold if low_threshold is not None else self.alerts_cfg.get("low_confidence_threshold", 0.50)

        conn = get_connection(self.custom_db_path)
        try:
            cursor = conn.execute(
                """
                SELECT q.subject, s.combined
                FROM queries q
                JOIN signals s ON q.id = s.query_id
                ORDER BY q.created_at DESC, q.id DESC
                LIMIT 30
                """
            )
            rows = cursor.fetchall()
            if not rows:
                return []

            # Group recent scores by subject
            subject_low_counts: Dict[str, int] = {}
            for row in rows:
                subj = row["subject"] or "General Medicine"
                score = row["combined"]
                if score < low_t:
                    subject_low_counts[subj] = subject_low_counts.get(subj, 0) + 1

            triggered: List[Dict[str, Any]] = []
            for subj, count in subject_low_counts.items():
                if count >= c_limit:
                    triggered.append({
                        "alert_type": f"repeated_low_confidence_{subj}",
                        "severity": "warning",
                        "message": (
                            f"Repeated low confidence in '{subj}': {count} queries scored below {low_t:.2f} "
                            f"(threshold: {c_limit} occurrences)."
                        ),
                        "subject": subj,
                        "metric_value": count,
                    })
            return triggered
        finally:
            conn.close()

    def run_all_checks(self, deduplicate_minutes: int = 30) -> List[Dict[str, Any]]:
        """Evaluate all alert rules and persist new non-duplicate alerts in SQLite."""
        new_alerts: List[Dict[str, Any]] = []

        # 1. High Escalation Rate
        alert1 = self.check_high_escalation_rate()
        if alert1:
            if not has_recent_alert_of_type(alert1["alert_type"], within_minutes=deduplicate_minutes, custom_path=self.custom_db_path):
                insert_alert(alert1["alert_type"], alert1["message"], alert1["severity"], custom_path=self.custom_db_path)
                new_alerts.append(alert1)

        # 2. Review Backlog
        alert2 = self.check_review_backlog()
        if alert2:
            if not has_recent_alert_of_type(alert2["alert_type"], within_minutes=deduplicate_minutes, custom_path=self.custom_db_path):
                insert_alert(alert2["alert_type"], alert2["message"], alert2["severity"], custom_path=self.custom_db_path)
                new_alerts.append(alert2)

        # 3. Repeated Low Confidence
        alerts3 = self.check_repeated_low_confidence()
        for a3 in alerts3:
            if not has_recent_alert_of_type(a3["alert_type"], within_minutes=deduplicate_minutes, custom_path=self.custom_db_path):
                insert_alert(a3["alert_type"], a3["message"], a3["severity"], custom_path=self.custom_db_path)
                new_alerts.append(a3)

        return new_alerts


def check_and_record_alerts(custom_db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Convenience function to trigger alert evaluation."""
    engine = AlertEngine(custom_db_path=custom_db_path)
    return engine.run_all_checks()
