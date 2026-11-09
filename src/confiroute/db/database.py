"""SQLite persistence layer and query helpers for ConfiRoute."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import sqlite3
import uuid
from confiroute.config import get_config
from confiroute.routing.router import RouteDecision

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_db_path(custom_path: Optional[Path] = None) -> Path:
    """Return configured database path or custom override."""
    if custom_path:
        return custom_path
    config = get_config()
    db_path = config.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_connection(custom_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open SQLite connection with Row factory and WAL mode enabled."""
    db_path = get_db_path(custom_path)
    conn = sqlite3.connect(str(db_path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(custom_path: Optional[Path] = None) -> None:
    """Execute schema.sql to ensure all required tables and indices exist."""
    conn = get_connection(custom_path)
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def insert_query(
    conn: sqlite3.Connection,
    query_id: str,
    question: str,
    options: Dict[str, str],
    correct_letter: Optional[str] = None,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
) -> None:
    """Insert a new question record into queries table."""
    conn.execute(
        """
        INSERT OR REPLACE INTO queries (id, question, options_json, correct_letter, subject, topic)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            query_id,
            question,
            json.dumps(options),
            correct_letter,
            subject or "General Medicine",
            topic or "General",
        ),
    )


def insert_signals(
    conn: sqlite3.Connection,
    query_id: str,
    s1: Optional[float],
    s2: Optional[float],
    s3: Optional[float],
    combined: float,
    mean_logprob: Optional[float] = None,
    agreement_stats: Optional[Dict[str, Any]] = None,
    effective_weights: Optional[Dict[str, float]] = None,
) -> None:
    """Insert confidence signal measurements."""
    conn.execute(
        """
        INSERT INTO signals (query_id, s1, s2, s3, combined, mean_logprob, agreement_stats_json, effective_weights_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            query_id,
            s1,
            s2,
            s3,
            combined,
            mean_logprob,
            json.dumps(agreement_stats) if agreement_stats else None,
            json.dumps(effective_weights) if effective_weights else None,
        ),
    )


def insert_route(
    conn: sqlite3.Connection,
    query_id: str,
    decision: RouteDecision,
) -> None:
    """Insert routing decision record."""
    conn.execute(
        """
        INSERT INTO routes (query_id, route, status, color, ai_draft_answer, final_answer, tier_used, is_high_risk, risk_reason, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            query_id,
            decision.route,
            decision.status,
            decision.color,
            decision.ai_draft_answer,
            decision.final_answer,
            decision.tier_used,
            1 if decision.is_high_risk else 0,
            decision.risk_reason,
            decision.reason,
        ),
    )


def insert_costs(
    conn: sqlite3.Connection,
    query_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    real_cost: float,
    equivalent_cost: float,
    latency_ms: float = 0.0,
) -> None:
    """Insert cost and token usage record."""
    conn.execute(
        """
        INSERT INTO costs (query_id, prompt_tokens, completion_tokens, total_tokens, real_cost, equivalent_cost, latency_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            query_id,
            prompt_tokens,
            completion_tokens,
            prompt_tokens + completion_tokens,
            real_cost,
            equivalent_cost,
            latency_ms,
        ),
    )


def save_pipeline_execution(
    question: str,
    options: Dict[str, str],
    decision: RouteDecision,
    query_id: Optional[str] = None,
    correct_letter: Optional[str] = None,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    custom_path: Optional[Path] = None,
) -> str:
    """Atomic helper that commits the full query, signals, route, and cost in one transaction."""
    qid = query_id or f"q-{uuid.uuid4().hex[:10]}"
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        with conn:
            insert_query(
                conn,
                query_id=qid,
                question=question,
                options=options,
                correct_letter=correct_letter,
                subject=subject,
                topic=topic,
            )
            insert_signals(
                conn,
                query_id=qid,
                s1=decision.scores.get("s1"),
                s2=decision.scores.get("s2"),
                s3=decision.scores.get("s3"),
                combined=decision.scores.get("combined", 0.0),
            )
            insert_route(conn, query_id=qid, decision=decision)
            tokens = decision.tokens_used
            costs = decision.cost_metadata
            insert_costs(
                conn,
                query_id=qid,
                prompt_tokens=tokens.get("prompt_tokens", 0),
                completion_tokens=tokens.get("completion_tokens", 0),
                real_cost=costs.get("real_cost", 0.0),
                equivalent_cost=costs.get("equivalent_cost", 0.0),
            )
        return qid
    finally:
        conn.close()


def record_review_decision(
    query_id: str,
    reviewer_name: str,
    decision: str,
    corrected_answer: Optional[str] = None,
    notes: Optional[str] = None,
    custom_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Record reviewer action (approved, edited, rejected) and update case status in SQLite."""
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        with conn:
            # Check existing route
            route_row = conn.execute(
                "SELECT id, status, ai_draft_answer FROM routes WHERE query_id = ? ORDER BY id DESC LIMIT 1",
                (query_id,),
            ).fetchone()

            if not route_row:
                raise ValueError(f"No routing record found for query_id '{query_id}'")

            current_draft = route_row["ai_draft_answer"]
            decision_norm = decision.strip().lower()

            # Insert into reviews table
            conn.execute(
                """
                INSERT INTO reviews (query_id, reviewer_name, decision, corrected_answer, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    reviewer_name.strip(),
                    decision_norm,
                    corrected_answer.strip().upper() if corrected_answer else None,
                    notes.strip() if notes else None,
                ),
            )

            # Update routes status and final answer
            if decision_norm == "approved":
                new_status = "completed"
                final_ans = current_draft
            elif decision_norm == "edited":
                new_status = "completed"
                final_ans = corrected_answer.strip().upper() if corrected_answer else current_draft
            elif decision_norm == "rejected":
                new_status = "rejected"
                final_ans = None
            else:
                raise ValueError(f"Invalid review decision '{decision}'. Expected: approved, edited, rejected.")

            conn.execute(
                """
                UPDATE routes
                SET status = ?, final_answer = ?
                WHERE query_id = ?
                """,
                (new_status, final_ans, query_id),
            )

        return {
            "query_id": query_id,
            "decision": decision_norm,
            "updated_status": new_status,
            "final_answer": final_ans,
            "reviewer_name": reviewer_name,
        }
    finally:
        conn.close()


def get_pending_reviews(limit: int = 50, custom_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve cases awaiting human clinician review."""
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cursor = conn.execute(
            """
            SELECT
                q.id,
                q.question,
                q.options_json,
                q.subject,
                q.topic,
                q.created_at,
                s.s1,
                s.s2,
                s.s3,
                s.combined,
                r.route,
                r.status,
                r.color,
                r.ai_draft_answer,
                r.tier_used,
                r.is_high_risk,
                r.risk_reason,
                r.reason
            FROM queries q
            JOIN routes r ON q.id = r.query_id
            LEFT JOIN signals s ON q.id = s.query_id
            WHERE r.status IN ('pending_human', 'pending_tier2')
            ORDER BY q.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = []
        for r in cursor.fetchall():
            item = dict(r)
            try:
                item["options"] = json.loads(item.get("options_json") or "{}")
            except Exception:
                item["options"] = {}
            rows.append(item)
        return rows
    finally:
        conn.close()


def get_resolved_reviews(limit: int = 50, custom_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve cases that have been reviewed by a human with reviewer notes and decisions."""
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cursor = conn.execute(
            """
            SELECT
                rv.id as review_id,
                rv.query_id,
                rv.reviewer_name,
                rv.decision,
                rv.corrected_answer,
                rv.notes,
                rv.reviewed_at,
                q.question,
                r.ai_draft_answer,
                r.final_answer,
                r.status as route_status,
                r.reason
            FROM reviews rv
            JOIN queries q ON rv.query_id = q.id
            JOIN routes r ON rv.query_id = r.query_id
            ORDER BY rv.reviewed_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_query_result(query_id: str, custom_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Fetch status and current outcome for a single query."""
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cursor = conn.execute(
            """
            SELECT
                q.id,
                q.question,
                q.options_json,
                q.created_at,
                s.s1,
                s.s2,
                s.s3,
                s.combined,
                r.route,
                r.status,
                r.color,
                r.ai_draft_answer,
                r.final_answer,
                r.tier_used,
                r.is_high_risk,
                r.risk_reason,
                r.reason,
                c.equivalent_cost
            FROM queries q
            LEFT JOIN signals s ON q.id = s.query_id
            LEFT JOIN routes r ON q.id = r.query_id
            LEFT JOIN costs c ON q.id = c.query_id
            WHERE q.id = ?
            ORDER BY r.id DESC
            LIMIT 1
            """,
            (query_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        try:
            res["options"] = json.loads(res.get("options_json") or "{}")
        except Exception:
            res["options"] = {}
        return res
    finally:
        conn.close()


def get_system_stats(custom_path: Optional[Path] = None) -> Dict[str, Any]:
    """Calculate aggregate routing and review statistics."""
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        total_queries = conn.execute("SELECT count(*) as c FROM queries").fetchone()["c"]
        direct_count = conn.execute("SELECT count(*) as c FROM routes WHERE route = 'direct'").fetchone()["c"]
        tier2_count = conn.execute("SELECT count(*) as c FROM routes WHERE route = 'tier2'").fetchone()["c"]
        human_count = conn.execute("SELECT count(*) as c FROM routes WHERE route = 'human'").fetchone()["c"]
        pending_reviews = conn.execute("SELECT count(*) as c FROM routes WHERE status IN ('pending_human', 'pending_tier2')").fetchone()["c"]
        approved_reviews = conn.execute("SELECT count(*) as c FROM reviews WHERE decision = 'approved'").fetchone()["c"]
        edited_reviews = conn.execute("SELECT count(*) as c FROM reviews WHERE decision = 'edited'").fetchone()["c"]
        rejected_reviews = conn.execute("SELECT count(*) as c FROM reviews WHERE decision = 'rejected'").fetchone()["c"]

        return {
            "total_queries": total_queries,
            "routes": {
                "direct": direct_count,
                "tier2": tier2_count,
                "human": human_count,
            },
            "reviews": {
                "pending": pending_reviews,
                "approved": approved_reviews,
                "edited": edited_reviews,
                "rejected": rejected_reviews,
            },
        }
    finally:
        conn.close()


def get_recent_history(limit: int = 20, custom_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve recent queries with combined scores, routes, and reasons."""
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cursor = conn.execute(
            """
            SELECT
                q.id,
                q.question,
                q.created_at,
                s.s1,
                s.s2,
                s.s3,
                s.combined,
                r.route,
                r.status,
                r.color,
                r.ai_draft_answer,
                r.final_answer,
                r.is_high_risk,
                r.risk_reason,
                r.reason,
                c.equivalent_cost
            FROM queries q
            LEFT JOIN signals s ON q.id = s.query_id
            LEFT JOIN routes r ON q.id = r.query_id
            LEFT JOIN costs c ON q.id = c.query_id
            ORDER BY q.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    finally:
        conn.close()


def insert_alert(
    alert_type: str,
    message: str,
    severity: str = "warning",
    custom_path: Optional[Path] = None,
) -> int:
    """Insert a new alert record into SQLite alerts table."""
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO alerts (alert_type, message, severity)
            VALUES (?, ?, ?)
            """,
            (alert_type, message, severity),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_active_alerts(
    limit: int = 50,
    custom_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve recent alerts ordered by newest first."""
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cursor = conn.execute(
            """
            SELECT id, alert_type, message, severity, created_at
            FROM alerts
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def has_recent_alert_of_type(
    alert_type: str,
    within_minutes: int = 60,
    custom_path: Optional[Path] = None,
) -> bool:
    """Check if an alert of the specified type was triggered recently to prevent duplicates."""
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cursor = conn.execute(
            """
            SELECT count(*) as c
            FROM alerts
            WHERE alert_type = ?
              AND created_at >= datetime('now', '-' || ? || ' minutes')
            """,
            (alert_type, within_minutes),
        )
        row = cursor.fetchone()
        return bool(row and row["c"] > 0)
    finally:
        conn.close()


def clear_alerts(custom_path: Optional[Path] = None) -> None:
    """Clear all alerts (e.g., for test setup)."""
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        conn.execute("DELETE FROM alerts")
        conn.commit()
    finally:
        conn.close()


def get_dashboard_query_records(
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 1000,
    custom_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve joined query records for dashboard filtering and charts."""
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        query = """
            SELECT
                q.id,
                q.question,
                q.correct_letter,
                q.subject,
                q.topic,
                q.created_at,
                s.s1,
                s.s2,
                s.s3,
                s.combined,
                r.route,
                r.status,
                r.color,
                r.ai_draft_answer,
                r.final_answer,
                r.is_high_risk,
                r.risk_reason,
                r.reason,
                c.latency_ms,
                c.equivalent_cost,
                c.prompt_tokens,
                c.completion_tokens,
                c.total_tokens,
                rev.decision AS review_decision,
                rev.corrected_answer
            FROM queries q
            LEFT JOIN signals s ON q.id = s.query_id
            LEFT JOIN routes r ON q.id = r.query_id
            LEFT JOIN costs c ON q.id = c.query_id
            LEFT JOIN reviews rev ON q.id = rev.query_id
            WHERE 1=1
        """
        params: List[Any] = []
        if subject and subject != "All":
            query += " AND q.subject = ?"
            params.append(subject)
        if topic and topic != "All":
            query += " AND q.topic = ?"
            params.append(topic)

        query += " ORDER BY q.created_at DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
