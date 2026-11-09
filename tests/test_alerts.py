"""Unit tests for the ConfiRoute alerts engine and SQLite persistence."""

import tempfile
from pathlib import Path
import pytest

from confiroute.db.database import (
    init_db,
    insert_query,
    insert_signals,
    save_pipeline_execution,
    insert_alert,
    get_active_alerts,
    clear_alerts,
    has_recent_alert_of_type,
)
from confiroute.alerts.alerts import AlertEngine, check_and_record_alerts
from confiroute.routing.router import RouteDecision


@pytest.fixture
def temp_db():
    """Create a clean isolated SQLite database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_alerts.db"
        init_db(db_path)
        yield db_path


def test_insert_and_get_active_alerts(temp_db):
    """Verify manual alert insertion and retrieval."""
    alert_id = insert_alert(
        alert_type="high_escalation_rate",
        message="Escalation rate exceeded 60%",
        severity="warning",
        custom_path=temp_db,
    )
    assert alert_id > 0

    alerts = get_active_alerts(custom_path=temp_db)
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "high_escalation_rate"
    assert alerts[0]["severity"] == "warning"


def test_alert_deduplication(temp_db):
    """Verify has_recent_alert_of_type prevents duplicate alert spam."""
    insert_alert(
        alert_type="review_backlog",
        message="Backlog high",
        severity="warning",
        custom_path=temp_db,
    )
    assert has_recent_alert_of_type("review_backlog", within_minutes=60, custom_path=temp_db) is True
    assert has_recent_alert_of_type("different_alert", within_minutes=60, custom_path=temp_db) is False


def test_alert_engine_backlog_trigger(temp_db):
    """Verify Alert 2: Review backlog triggers when pending reviews exceed threshold."""
    engine = AlertEngine(custom_db_path=temp_db)

    # Insert 12 pending cases (threshold default is 10)
    for i in range(12):
        dec = RouteDecision(
            route="human",
            status="pending_human",
            color="red",
            final_answer=None,
            ai_draft_answer="A",
            scores={"s1": 0.3, "s2": 0.3, "s3": 0.3, "combined": 0.3},
            is_high_risk=False,
            risk_reason=None,
            reason="Low confidence",
            tier_used="tier1",
            tokens_used={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
            cost_metadata={"real_cost": 0.0, "equivalent_cost": 0.0001, "currency": "USD"},
        )
        save_pipeline_execution(
            query_id=f"q-backlog-{i}",
            question=f"Question {i}",
            options={"A": "A", "B": "B"},
            decision=dec,
            custom_path=temp_db,
        )

    alert = engine.check_review_backlog(threshold=10)
    assert alert is not None
    assert alert["alert_type"] == "review_backlog"
    assert alert["metric_value"] == 12


def test_alert_engine_high_escalation_rate(temp_db):
    """Verify Alert 1: High escalation rate triggers over recent window."""
    engine = AlertEngine(custom_db_path=temp_db)

    # Insert 10 queries, 8 of which are human escalation (80% > 50% threshold)
    for i in range(10):
        is_esc = i < 8
        dec = RouteDecision(
            route="human" if is_esc else "direct",
            status="pending_human" if is_esc else "completed",
            color="red" if is_esc else "green",
            final_answer="A" if not is_esc else None,
            ai_draft_answer="A",
            scores={"s1": 0.3 if is_esc else 0.9, "s2": 0.3, "s3": 0.3, "combined": 0.3 if is_esc else 0.9},
            is_high_risk=False,
            risk_reason=None,
            reason="Test",
            tier_used="tier1",
            tokens_used={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
            cost_metadata={"real_cost": 0.0, "equivalent_cost": 0.0001, "currency": "USD"},
        )
        save_pipeline_execution(
            query_id=f"q-esc-{i}",
            question=f"Question {i}",
            options={"A": "A", "B": "B"},
            decision=dec,
            custom_path=temp_db,
        )

    alert = engine.check_high_escalation_rate(window_size=10, threshold=0.50)
    assert alert is not None
    assert alert["alert_type"] == "high_escalation_rate"
    assert alert["metric_value"] == 0.80


def test_alert_engine_repeated_low_confidence(temp_db):
    """Verify Alert 3: Repeated low confidence triggers when multiple queries score low for a subject."""
    engine = AlertEngine(custom_db_path=temp_db)

    # Insert 4 queries in Pharmacology with low confidence (0.35 < 0.50)
    for i in range(4):
        qid = f"q-low-{i}"
        dec = RouteDecision(
            route="human",
            status="pending_human",
            color="red",
            final_answer=None,
            ai_draft_answer="B",
            scores={"s1": 0.35, "s2": 0.35, "s3": 0.35, "combined": 0.35},
            is_high_risk=False,
            risk_reason=None,
            reason="Low score",
            tier_used="tier1",
            tokens_used={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
            cost_metadata={"real_cost": 0.0, "equivalent_cost": 0.0001, "currency": "USD"},
        )
        save_pipeline_execution(
            query_id=qid,
            question=f"Pharma Question {i}",
            options={"A": "A", "B": "B"},
            decision=dec,
            subject="Pharmacology",
            custom_path=temp_db,
        )

    alerts = engine.check_repeated_low_confidence(consecutive_limit=3, low_threshold=0.50)
    assert len(alerts) >= 1
    assert "Pharmacology" in alerts[0]["alert_type"]
    assert alerts[0]["metric_value"] == 4
