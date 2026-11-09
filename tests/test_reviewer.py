"""Tests for human review queue and clinician decision persistence."""

import tempfile
from pathlib import Path
import pytest

from confiroute.db.database import (
    init_db,
    save_pipeline_execution,
    record_review_decision,
    get_pending_reviews,
    get_resolved_reviews,
    get_query_result,
)
from confiroute.routing.router import RouteDecision


def create_sample_pending_case(db_path: Path, query_id: str = "q-test-01") -> str:
    decision = RouteDecision(
        route="human",
        status="pending_human",
        color="red",
        final_answer=None,  # Withheld
        ai_draft_answer="B",
        scores={"s1": 0.40, "s2": 0.33, "s3": 0.45, "combined": 0.39},
        is_high_risk=False,
        risk_reason=None,
        reason="Low confidence: held for human review",
        tier_used="tier1",
        tokens_used={"prompt_tokens": 40, "completion_tokens": 5, "total_tokens": 45},
        cost_metadata={"real_cost": 0.0, "equivalent_cost": 0.00005},
    )

    save_pipeline_execution(
        question="What is the treatment for refractory celiac disease?",
        options={"A": "Steroids", "B": "Gluten diet", "C": "Loperamide", "D": "Penicillin"},
        decision=decision,
        query_id=query_id,
        custom_path=db_path,
    )
    return query_id


def test_reviewer_approval_releases_ai_draft():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test.db"
        qid = create_sample_pending_case(test_db, "case-approve")

        # Initial state
        pending = get_pending_reviews(custom_path=test_db)
        assert len(pending) == 1
        assert pending[0]["id"] == qid
        assert pending[0]["status"] == "pending_human"

        # Reviewer approves
        res = record_review_decision(
            query_id=qid,
            reviewer_name="Dr. Smith",
            decision="approved",
            notes="Clinically valid draft",
            custom_path=test_db,
        )

        assert res["decision"] == "approved"
        assert res["updated_status"] == "completed"
        assert res["final_answer"] == "B"  # Released!

        # Should no longer be pending
        pending_after = get_pending_reviews(custom_path=test_db)
        assert len(pending_after) == 0

        # Should appear in resolved audit log
        resolved = get_resolved_reviews(custom_path=test_db)
        assert len(resolved) == 1
        assert resolved[0]["query_id"] == qid
        assert resolved[0]["decision"] == "approved"
        assert resolved[0]["final_answer"] == "B"


def test_reviewer_edit_replaces_with_correction():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test.db"
        qid = create_sample_pending_case(test_db, "case-edit")

        # Reviewer corrects draft from 'B' to 'A'
        res = record_review_decision(
            query_id=qid,
            reviewer_name="Dr. Patel",
            decision="edited",
            corrected_answer="A",
            notes="Gluten free diet and corticosteroids are required",
            custom_path=test_db,
        )

        assert res["decision"] == "edited"
        assert res["updated_status"] == "completed"
        assert res["final_answer"] == "A"  # Corrected option released!

        # Check in DB
        row = get_query_result(qid, custom_path=test_db)
        assert row["status"] == "completed"
        assert row["final_answer"] == "A"
        assert row["ai_draft_answer"] == "B"  # Original draft preserved for audit!


def test_reviewer_rejection_withholds_answer():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test.db"
        qid = create_sample_pending_case(test_db, "case-reject")

        # Reviewer rejects case
        res = record_review_decision(
            query_id=qid,
            reviewer_name="Dr. Adams",
            decision="rejected",
            notes="Question is clinically flawed/unanswerable safely",
            custom_path=test_db,
        )

        assert res["decision"] == "rejected"
        assert res["updated_status"] == "rejected"
        assert res["final_answer"] is None  # Rejected cases must NOT release an answer!

        row = get_query_result(qid, custom_path=test_db)
        assert row["status"] == "rejected"
        assert row["final_answer"] is None


def test_invalid_decision_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test.db"
        qid = create_sample_pending_case(test_db, "case-invalid")

        with pytest.raises(ValueError):
            record_review_decision(
                query_id=qid,
                reviewer_name="Dr. X",
                decision="maybe",
                custom_path=test_db,
            )
