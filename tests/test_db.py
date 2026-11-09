"""Tests for SQLite database initialization, transactions, and queries."""

import tempfile
from pathlib import Path
from confiroute.db.database import (
    init_db,
    get_connection,
    save_pipeline_execution,
    get_recent_history,
)
from confiroute.routing.router import RouteDecision


def test_init_db_creates_tables():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test.db"
        init_db(test_db)
        conn = get_connection(test_db)
        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            ).fetchall()
            names = {t["name"] for t in tables}
            expected = {"queries", "signals", "routes", "reviews", "costs", "alerts"}
            assert expected.issubset(names)
        finally:
            conn.close()


def test_save_pipeline_and_retrieve_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test.db"
        decision = RouteDecision(
            route="direct",
            status="completed",
            color="green",
            final_answer="A",
            ai_draft_answer="A",
            scores={"s1": 0.85, "s2": 0.90, "s3": 0.80, "combined": 0.85},
            is_high_risk=False,
            risk_reason=None,
            reason="High confidence score",
            tier_used="tier1",
            tokens_used={"prompt_tokens": 50, "completion_tokens": 10},
            cost_metadata={"real_cost": 0.0, "equivalent_cost": 0.00005},
        )

        qid = save_pipeline_execution(
            question="What is the function of red blood cells?",
            options={"A": "Oxygen transport", "B": "Clotting", "C": "Immunity", "D": "Digestion"},
            decision=decision,
            custom_path=test_db,
        )

        assert qid.startswith("q-")

        history = get_recent_history(limit=5, custom_path=test_db)
        assert len(history) == 1
        record = history[0]
        assert record["id"] == qid
        assert record["route"] == "direct"
        assert record["color"] == "green"
        assert record["combined"] == 0.85
