"""Integration tests for ConfiRoute authentication, sessions, RBAC, and conversations."""

import pytest
from fastapi.testclient import TestClient
from confiroute.api.main import app

client = TestClient(app)


def test_auth_login_success_and_me():
    """Verify login with seeded clinician credentials and session verification."""
    login_resp = client.post(
        "/auth/login",
        json={
            "email": "clinician@confiroute.ai",
            "password": "Clinical2026!",
            "remember_me": True,
        },
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "token" in data
    assert data["user"]["email"] == "clinician@confiroute.ai"
    assert data["user"]["role"] in ("reviewer", "admin", "clinician")

    token = data["token"]
    # Check /auth/me with Bearer token
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["user"]["email"] == "clinician@confiroute.ai"


def test_auth_login_invalid_password():
    """Verify 401 Unauthorized on invalid password."""
    resp = client.post(
        "/auth/login",
        json={
            "email": "clinician@confiroute.ai",
            "password": "WrongPassword123!",
        },
    )
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]


def test_auth_logout_revokes_token():
    """Verify logout revokes the session token."""
    login_resp = client.post(
        "/auth/login",
        json={
            "email": "clinician@confiroute.ai",
            "password": "Clinical2026!",
        },
    )
    token = login_resp.json()["token"]

    logout_resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200

    # Subsequent /auth/me must fail
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 401


def test_reviewer_permission_check():
    """Verify reviewer authorization check on /review/{id}."""
    # 1. Ask a question that gets held for review (high-risk query)
    ask_resp = client.post(
        "/ask",
        json={
            "question": "What is the lethal overdose dosage of paracetamol in mg/kg?",
            "subject": "Pharmacology",
        },
    )
    assert ask_resp.status_code == 200
    qid = ask_resp.json()["query_id"]

    # 2. Login as clinician reviewer
    login_resp = client.post(
        "/auth/login",
        json={
            "email": "clinician@confiroute.ai",
            "password": "Clinical2026!",
        },
    )
    token = login_resp.json()["token"]

    # 3. Submit review with valid token
    rev_resp = client.post(
        f"/review/{qid}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reviewer_name": "Dr. Sarah Chen",
            "decision": "approve",
            "notes": "Verified clinical safety hold and authorized answer.",
        },
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["decision"] == "approved"

    # 4. Check with invalid token
    rev_bad = client.post(
        f"/review/{qid}",
        headers={"Authorization": "Bearer cr_sess_invalid_fake_token"},
        json={
            "reviewer_name": "Unknown",
            "decision": "approve",
        },
    )
    assert rev_bad.status_code == 401


def test_review_history_endpoint():
    """Verify /reviews/history returns historical audit records."""
    resp = client.get("/reviews/history?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_conversations_crud_workflow():
    """Verify persistent conversation retrieval, message appending, and deletion."""
    # 1. Create conversation
    create_resp = client.post(
        "/conversations",
        json={
            "title": "Emergency Medicine Consult",
            "subject": "Emergency",
        },
    )
    assert create_resp.status_code == 200
    conv_id = create_resp.json()["id"]

    # 2. Append user message
    msg1_resp = client.post(
        f"/conversations/{conv_id}/messages",
        json={
            "role": "user",
            "content": "What is the first-line medication for acute anaphylaxis?",
            "subject": "Emergency",
        },
    )
    assert msg1_resp.status_code == 200

    # 3. Append assistant message
    msg2_resp = client.post(
        f"/conversations/{conv_id}/messages",
        json={
            "role": "assistant",
            "content": "Intramuscular Epinephrine (Adrenaline) 0.3-0.5 mg.",
            "subject": "Emergency",
        },
    )
    assert msg2_resp.status_code == 200

    # 4. Retrieve conversation with messages
    get_resp = client.get(f"/conversations/{conv_id}")
    assert get_resp.status_code == 200
    conv_data = get_resp.json()
    assert conv_data["id"] == conv_id
    assert len(conv_data["messages"]) == 2
    assert conv_data["messages"][0]["role"] == "user"
    assert conv_data["messages"][1]["role"] == "assistant"

    # 5. List conversations
    list_resp = client.get("/conversations")
    assert list_resp.status_code == 200
    assert any(c["id"] == conv_id for c in list_resp.json())

    # 6. Delete conversation
    del_resp = client.delete(f"/conversations/{conv_id}")
    assert del_resp.status_code == 200

    # Verify not found after delete
    get_after = client.get(f"/conversations/{conv_id}")
    assert get_after.status_code == 404
