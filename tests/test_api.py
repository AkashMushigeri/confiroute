"""Tests for FastAPI backend endpoints."""

import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from confiroute.api.main import app
from confiroute.db.database import init_db

client = TestClient(app)


def test_api_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "ConfiRoute" in data["app_name"]


def test_api_ask_direct_green():
    payload = {
        "question": "What cell produces insulin?",
        "options": {"A": "Beta cells", "B": "Alpha cells", "C": "Delta cells", "D": "Acinar cells"},
        "model_key": "tier1",
        "provider": "mock",
        "simulated_level": "high",
    }
    resp = client.post("/ask", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "query_id" in data
    assert data["route"] in {"direct", "tier2", "human"}
    assert data["ai_draft_answer"] is not None


def test_api_ask_high_risk_red():
    payload = {
        "question": "What is the lethal overdose limit of potassium chloride bolus and emergency protocol?",
        "options": {"A": "100 mEq", "B": "20 mEq", "C": "10 mEq", "D": "5 mEq"},
        "model_key": "tier1",
        "provider": "mock",
    }
    resp = client.post("/ask", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["route"] == "human"
    assert data["status"] == "pending_human"
    assert data["color"] == "red"
    assert data["final_answer"] is None  # Withheld
    assert data["is_high_risk"] is True


def test_api_queue_and_review_workflow():
    # Submit low confidence query
    ask_payload = {
        "question": "Very uncertain ambiguous medical scenario?",
        "options": {"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"},
        "model_key": "tier1",
        "provider": "mock",
        "simulated_level": "low",
    }
    ask_resp = client.post("/ask", json=ask_payload)
    assert ask_resp.status_code == 200
    qid = ask_resp.json()["query_id"]

    # Check queue
    queue_resp = client.get("/queue")
    assert queue_resp.status_code == 200
    queue = queue_resp.json()
    assert any(item["id"] == qid for item in queue)

    # Review approve
    review_payload = {
        "reviewer_name": "Dr. Sarah",
        "decision": "approved",
        "notes": "Reviewed and validated draft",
    }
    rev_resp = client.post(f"/review/{qid}", json=review_payload)
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["updated_status"] == "completed"
    assert rev_data["final_answer"] is not None

    # Check result endpoint
    res_resp = client.get(f"/result/{qid}")
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "completed"


def test_api_result_not_found():
    resp = client.get("/result/non_existent_query_99999")
    assert resp.status_code == 404


def test_api_stats():
    resp = client.get("/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert "total_queries" in stats
    assert "routes" in stats
    assert "reviews" in stats


def test_api_ask_without_options():
    payload = {
        "question": "Which vitamin deficiency causes scurvy?",
        "model_key": "tier1",
        "provider": "mock",
    }
    resp = client.post("/ask", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "query_id" in data
    assert data["case"] is not None
    assert data["case"]["options"] is not None


def test_api_cases_list():
    resp = client.get("/cases?limit=10")
    assert resp.status_code == 200
    cases = resp.json()
    assert isinstance(cases, list)
    if cases:
        c = cases[0]
        assert "id" in c
        assert "score" in c
        assert "route" in c
        assert "signals" in c


def test_api_compare_systems():
    payload = {
        "question": "What is the recommended treatment for anaphylaxis?",
        "options": {"A": "Intramuscular Epinephrine", "B": "Oral Diphenhydramine", "C": "Inhaled Albuterol", "D": "IV Hydrocortisone"},
        "simulated_level": "high",
        "provider": "mock",
    }
    resp = client.post("/compare", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "unrouted" in data
    assert "confiroute" in data
    assert data["unrouted"]["answer"] is not None
    assert data["confiroute"]["score"] >= 0


def test_api_alerts():
    resp = client.get("/alerts")
    assert resp.status_code == 200
    alerts = resp.json()
    assert isinstance(alerts, list)


def test_api_export_csv():
    resp = client.get("/export/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "id,ts,question" in resp.text

