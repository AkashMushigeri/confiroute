"""Supabase Cloud Database & Persistence Verification Script.

Executes end-to-end verification of cloud PostgreSQL connectivity, schema tables,
user registration, authentication, conversation persistence across engine restarts,
routing log recording, human review tracking, and administrator oversight.
"""

import os
import sys
import time
from typing import Dict, Any

from dotenv import load_dotenv
load_dotenv()

from fastapi.testclient import TestClient
from confiroute.api.main import app
from confiroute.db.connection import (
    get_engine,
    test_cloud_connection,
    init_cloud_and_local_db,
    get_db_context,
)
from confiroute.db.models import (
    User,
    Profile,
    Conversation,
    Message,
    RoutingLog,
    HumanReview,
    AuditLog,
)

client = TestClient(app)


def print_step(title: str):
    print("\n" + "=" * 70)
    print(f"STEP: {title}")
    print("=" * 70)


def run_full_cloud_verification() -> Dict[str, Any]:
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "database_url_configured": bool(os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")),
        "dialect": None,
        "is_postgresql": False,
        "tables_verified": False,
        "registration_passed": False,
        "login_passed": False,
        "conversation_passed": False,
        "message_persistence_passed": False,
        "restart_survival_passed": False,
        "routing_log_passed": False,
        "human_review_passed": False,
        "admin_verification_passed": False,
        "rbac_rejection_passed": False,
    }

    print_step("1. Probing Database Connectivity & Schema Engine")
    db_status = test_cloud_connection()
    report["dialect"] = db_status["dialect"]
    report["is_postgresql"] = db_status["is_postgresql"]
    print(f"Connected: {db_status['connected']}")
    print(f"Dialect:   {db_status['dialect']}")
    print(f"Target is PostgreSQL / Supabase: {db_status['is_postgresql']}")
    print(f"Tables Found: {len(db_status['tables_found'])} tables -> {db_status['tables_found']}")

    if not db_status["required_tables_present"]:
        print(f"Initializing missing tables: {db_status['missing_tables']}")
        init_cloud_and_local_db()
        db_status = test_cloud_connection()

    assert db_status["required_tables_present"], f"Missing tables: {db_status['missing_tables']}"
    report["tables_verified"] = True
    print("[PASS] All required schema tables confirmed present.")

    # 2. User Registration
    print_step("2. User Registration")
    test_ts = int(time.time() * 1000)
    test_email = f"clinician_cloud_{test_ts}@hospital.org"
    reg_resp = client.post(
        "/auth/register",
        json={
            "email": test_email,
            "password": "CloudPassword2026!",
            "name": f"Dr. Cloud Specialist {test_ts % 1000}",
            "role": "clinician",
            "department": "Critical Care Medicine",
        },
    )
    assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
    reg_data = reg_resp.json()
    user_id = reg_data["user"]["id"]
    token = reg_data["token"]
    report["registration_passed"] = True
    print(f"[PASS] User registered: {test_email} (ID: {user_id})")

    # 3. User Login & Token Verification
    print_step("3. User Login & Token Verification")
    login_resp = client.post(
        "/auth/login",
        json={"email": test_email, "password": "CloudPassword2026!"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    login_data = login_resp.json()
    assert login_data["user"]["email"] == test_email
    token = login_data["token"]
    headers = {"Authorization": f"Bearer {token}"}
    report["login_passed"] = True
    print(f"[PASS] Login verified. Session token acquired.")

    # 4. Conversation Creation & Message Persistence
    print_step("4. Conversation Creation & Message Persistence")
    conv_id = f"cloud_conv_{test_ts}"
    conv_resp = client.post(
        "/conversations",
        headers=headers,
        json={
            "id": conv_id,
            "title": f"ICU Clinical Inquiry {test_ts % 1000}",
            "subject": "Intensive Care",
        },
    )
    assert conv_resp.status_code == 200, f"Conversation creation failed: {conv_resp.text}"
    report["conversation_passed"] = True
    print(f"[PASS] Conversation created: {conv_id}")

    # Send User Question Message
    msg_1_id = f"msg_user_{test_ts}"
    msg_1_resp = client.post(
        f"/conversations/{conv_id}/messages",
        headers=headers,
        json={
            "id": msg_1_id,
            "role": "user",
            "content": "Patient in septic shock refractory to norepinephrine. Next line vasopressor?",
            "subject": "Intensive Care",
        },
    )
    assert msg_1_resp.status_code == 200, f"User message save failed: {msg_1_resp.text}"

    # Evaluate query with ConfiRoute
    ask_resp = client.post(
        "/ask",
        json={
            "question": "In septic shock refractory to norepinephrine, what is the recommended second-line vasopressor according to Surviving Sepsis guidelines?",
            "options": {
                "A": "Vasopressin (up to 0.03 units/min)",
                "B": "High-dose dopamine monotherapy",
                "C": "Phenylephrine infusion only",
                "D": "Discontinue vasopressors immediately",
            },
            "subject": "Intensive Care",
        },
    )
    assert ask_resp.status_code == 200, f"Inference ask failed: {ask_resp.text}"
    ask_data = ask_resp.json()
    qid = ask_data["query_id"]

    # Append Assistant Response
    msg_2_id = f"msg_ai_{test_ts}"
    msg_2_resp = client.post(
        f"/conversations/{conv_id}/messages",
        headers=headers,
        json={
            "id": msg_2_id,
            "role": "assistant",
            "content": ask_data["final_answer"] or ask_data["ai_draft_answer"],
            "query_id": qid,
            "subject": "Intensive Care",
        },
    )
    assert msg_2_resp.status_code == 200
    report["message_persistence_passed"] = True
    print(f"[PASS] Messages persisted into conversation {conv_id}.")

    # 5. Database Restart & Persistence Survival Test
    print_step("5. Simulating Backend Restart & Discarding Connections")
    # Dispose active SQLAlchemy engine and recreate fresh pool
    engine = get_engine()
    engine.dispose()
    print("[INFO] Engine connections successfully disposed.")

    # Re-verify conversation retrieval with fresh connection
    re_get = client.get(f"/conversations/{conv_id}", headers=headers)
    assert re_get.status_code == 200, f"Retrieval after restart failed: {re_get.text}"
    conv_data = re_get.json()
    assert len(conv_data["messages"]) == 2, f"Expected 2 messages, got {len(conv_data['messages'])}"
    assert conv_data["messages"][0]["content"].startswith("Patient in septic shock")
    report["restart_survival_passed"] = True
    print(f"[PASS] Persistence verified across engine restart: 2/2 messages survived intact.")

    # 6. Routing Log Verification
    print_step("6. Routing Log Persistence Verification")
    logs_resp = client.get("/routing/logs?limit=10", headers=headers)
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert any(l["query_id"] == qid for l in logs), f"Query {qid} not found in routing_logs"
    report["routing_log_passed"] = True
    print(f"[PASS] Routing log for query {qid} confirmed in routing_logs table.")

    # 7. Human Review Persistence & Audit Log
    print_step("7. Human Review Persistence Verification")
    rev_resp = client.post(
        f"/review/{qid}",
        headers=headers,
        json={
            "reviewer_name": "Dr. Sarah Chen, MD",
            "decision": "approve",
            "notes": "Vasopressin second-line titration verified per Surviving Sepsis Campaign.",
        },
    )
    assert rev_resp.status_code == 200, f"Review submission failed: {rev_resp.text}"
    report["human_review_passed"] = True
    print(f"[PASS] Human review for case {qid} recorded.")

    # Direct DB inspection via SQLAlchemy context
    with get_db_context() as db:
        rev_record = db.query(HumanReview).filter(HumanReview.query_id == qid).first()
        assert rev_record is not None
        assert rev_record.decision == "approved"

        audit_entry = db.query(AuditLog).filter(AuditLog.resource_id == qid).first()
        assert audit_entry is not None
        assert audit_entry.action == "review_submit"
    print(f"[PASS] Direct database query confirmed HumanReview and AuditLog records.")

    # 8. Administrator Dashboard Verification
    print_step("8. Admin Dashboard & RBAC Access Verification")
    # Clinician token must be rejected with 403 on /admin/*
    assert client.get("/admin/users", headers=headers).status_code == 403
    assert client.get("/admin/stats", headers=headers).status_code == 403
    report["rbac_rejection_passed"] = True
    print("[PASS] Unauthorized access to /admin/* correctly rejected with HTTP 403 Forbidden.")

    # Admin Login
    admin_login = client.post(
        "/auth/login",
        json={"email": "admin@confiroute.ai", "password": "AdminSecure2026!"},
    )
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin reads users
    admin_users = client.get("/admin/users", headers=admin_headers)
    assert admin_users.status_code == 200
    user_list = admin_users.json()
    assert any(u["email"] == test_email for u in user_list)
    print(f"[PASS] Admin user directory verified ({len(user_list)} registered users visible).")

    # Admin reads stats
    admin_stats = client.get("/admin/stats", headers=admin_headers)
    assert admin_stats.status_code == 200
    stats = admin_stats.json()
    assert stats["total_conversations"] >= 1
    assert stats["total_routing_logs"] >= 1
    report["admin_verification_passed"] = True
    print(f"[PASS] Admin stats verified (Total convs: {stats['total_conversations']}, Queries: {stats['total_queries']}).")

    return report


if __name__ == "__main__":
    report = run_full_cloud_verification()
    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    for k, v in report.items():
        print(f" - {k:30}: {v}")
