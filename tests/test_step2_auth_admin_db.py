"""Comprehensive verification suite for Step 2:
Authentication, User Isolation, Cloud DB Integration, Routing Logs, and Admin Dashboard.
"""

import time
import pytest
from fastapi.testclient import TestClient
from confiroute.api.main import app
from confiroute.db.connection import get_db_context
from confiroute.db.models import User, Profile, Conversation, Message, RoutingLog, HumanReview, AuditLog

client = TestClient(app)


def test_user_registration_and_privilege_escalation_protection():
    """Verify registration succeeds and ordinary users cannot self-escalate to admin."""
    ts = int(time.time() * 1000)
    email = f"dr_jensen_{ts}@hospital.org"

    # Attempt to self-assign role='admin' without admin token
    reg_resp = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Password2026!",
            "name": "Dr. Clara Jensen",
            "role": "admin",  # should be downgraded to reviewer
            "department": "Cardiology",
        },
    )
    assert reg_resp.status_code == 200
    data = reg_resp.json()
    assert data["user"]["role"] == "reviewer"  # Prevented privilege escalation
    assert "token" in data

    # Duplicate registration fails
    dup_resp = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Password2026!",
            "name": "Dr. Clara Jensen",
            "role": "reviewer",
        },
    )
    assert dup_resp.status_code == 400
    assert "already registered" in dup_resp.json()["detail"]


def test_login_invalid_and_valid():
    """Verify login validation with correct and incorrect credentials."""
    # Invalid password
    resp = client.post(
        "/auth/login",
        json={
            "email": "clinician@confiroute.ai",
            "password": "WrongPassword123!",
        },
    )
    assert resp.status_code == 401

    # Valid password
    resp_ok = client.post(
        "/auth/login",
        json={
            "email": "clinician@confiroute.ai",
            "password": "Clinical2026!",
        },
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["user"]["email"] == "clinician@confiroute.ai"


def test_conversation_data_isolation():
    """Verify that User A cannot view, post to, or delete User B's conversation."""
    ts = int(time.time() * 1000)

    # Register User A
    user_a_email = f"user_a_{ts}@hospital.org"
    res_a = client.post(
        "/auth/register",
        json={"email": user_a_email, "password": "UserPassA123!", "name": "User Alpha", "role": "clinician"},
    )
    token_a = res_a.json()["token"]

    # Register User B
    user_b_email = f"user_b_{ts}@hospital.org"
    res_b = client.post(
        "/auth/register",
        json={"email": user_b_email, "password": "UserPassB123!", "name": "User Beta", "role": "clinician"},
    )
    token_b = res_b.json()["token"]

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B creates a private consultation
    conv_b_id = f"conv_b_{ts}"
    create_b = client.post(
        "/conversations",
        headers=headers_b,
        json={"id": conv_b_id, "title": "Oncology Patient Plan", "subject": "Oncology"},
    )
    assert create_b.status_code == 200

    # User A attempts to view User B's conversation -> 403 Forbidden
    view_attempt = client.get(f"/conversations/{conv_b_id}", headers=headers_a)
    assert view_attempt.status_code == 403
    assert "Access denied" in view_attempt.json()["detail"]

    # User A attempts to post message to User B's conversation -> 403 Forbidden
    post_attempt = client.post(
        f"/conversations/{conv_b_id}/messages",
        headers=headers_a,
        json={"role": "user", "content": "Unauthorized injection attempt"},
    )
    assert post_attempt.status_code == 403

    # User A attempts to delete User B's conversation -> 403 Forbidden
    del_attempt = client.delete(f"/conversations/{conv_b_id}", headers=headers_a)
    assert del_attempt.status_code == 403

    # User B can view and delete their own conversation
    view_ok = client.get(f"/conversations/{conv_b_id}", headers=headers_b)
    assert view_ok.status_code == 200
    assert view_ok.json()["title"] == "Oncology Patient Plan"

    del_ok = client.delete(f"/conversations/{conv_b_id}", headers=headers_b)
    assert del_ok.status_code == 200


def test_admin_rbac_and_dashboard_endpoints():
    """Verify RBAC: non-admins are rejected with 403, while admin accesses all endpoints."""
    # 1. Non-admin login
    res_clinician = client.post(
        "/auth/login",
        json={"email": "clinician@confiroute.ai", "password": "Clinical2026!"},
    )
    token_clinician = res_clinician.json()["token"]
    headers_clinician = {"Authorization": f"Bearer {token_clinician}"}

    # Non-admin attempts admin endpoints -> 403 Forbidden
    assert client.get("/admin/users", headers=headers_clinician).status_code == 403
    assert client.get("/admin/stats", headers=headers_clinician).status_code == 403
    assert client.get("/admin/conversations", headers=headers_clinician).status_code == 403
    assert client.get("/admin/reviews", headers=headers_clinician).status_code == 403

    # 2. Admin login
    res_admin = client.post(
        "/auth/login",
        json={"email": "admin@confiroute.ai", "password": "AdminSecure2026!"},
    )
    assert res_admin.status_code == 200
    token_admin = res_admin.json()["token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    # Admin access succeeds
    users_resp = client.get("/admin/users", headers=headers_admin)
    assert users_resp.status_code == 200
    users_list = users_resp.json()
    assert len(users_list) >= 2
    # Verify no passwords or salts are exposed
    for u in users_list:
        assert "password_hash" not in u
        assert "salt" not in u

    stats_resp = client.get("/admin/stats", headers=headers_admin)
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert "total_users" in stats_data
    assert "total_conversations" in stats_data
    assert "routes" in stats_data

    convs_resp = client.get("/admin/conversations", headers=headers_admin)
    assert convs_resp.status_code == 200
    assert isinstance(convs_resp.json(), list)

    revs_resp = client.get("/admin/reviews", headers=headers_admin)
    assert revs_resp.status_code == 200
    assert isinstance(revs_resp.json(), list)


def test_routing_logs_and_review_persistence():
    """Verify routing decisions are recorded in routing_logs and reviews in human_reviews."""
    # 1. Trigger ask
    ask_resp = client.post(
        "/ask",
        json={
            "question": "What is the primary contraindication for prescribing ACE inhibitors in bilateral renal artery stenosis?",
            "subject": "Nephrology",
        },
    )
    assert ask_resp.status_code == 200
    qid = ask_resp.json()["query_id"]

    # 2. Check routing logs
    res_login = client.post(
        "/auth/login",
        json={"email": "clinician@confiroute.ai", "password": "Clinical2026!"},
    )
    token = res_login.json()["token"]
    logs_resp = client.get("/routing/logs?limit=10", headers={"Authorization": f"Bearer {token}"})
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) > 0
    assert any(l["query_id"] == qid for l in logs)

    # 3. Submit review and check audit record
    rev_resp = client.post(
        f"/review/{qid}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reviewer_name": "Dr. Sarah Chen, MD",
            "decision": "approve",
            "notes": "Verified clinical accuracy for bilateral renal artery stenosis.",
        },
    )
    assert rev_resp.status_code == 200

    # 4. Verify in database via SQLAlchemy
    with get_db_context() as db:
        rev_record = db.query(HumanReview).filter(HumanReview.query_id == qid).first()
        assert rev_record is not None
        assert rev_record.decision == "approved"
        assert rev_record.reviewer_name == "Dr. Sarah Chen, MD"

        audit_record = db.query(AuditLog).filter(AuditLog.resource_id == qid).first()
        assert audit_record is not None
        assert audit_record.action == "review_submit"
