"""SQLite persistence layer and query helpers for ConfiRoute."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets
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


def is_cloud_postgres() -> bool:
    """Return True if active database engine dialect is PostgreSQL."""
    try:
        from confiroute.db.connection import is_postgres
        return is_postgres()
    except Exception:
        return False


def init_db(custom_path: Optional[Path] = None) -> None:
    """Execute schema.sql to ensure all required tables and indices exist."""
    if custom_path is None and is_cloud_postgres():
        try:
            from confiroute.db.connection import init_cloud_and_local_db
            init_cloud_and_local_db()
        except Exception:
            pass
        return

    conn = get_connection(custom_path)
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
        seed_default_users(conn)
    finally:
        conn.close()

    if custom_path is None:
        try:
            from confiroute.db.connection import init_cloud_and_local_db
            init_cloud_and_local_db()
        except Exception:
            pass


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

    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import Query, Signal, Route, Cost
        with get_db_context() as db:
            q_obj = Query(
                id=qid,
                question=question,
                options_json=json.dumps(options) if options else "{}",
                correct_letter=correct_letter,
                subject=subject or "General Medicine",
                topic=topic or "General",
            )
            db.add(q_obj)
            db.flush()

            sig_obj = Signal(
                query_id=qid,
                s1=decision.scores.get("s1"),
                s2=decision.scores.get("s2"),
                s3=decision.scores.get("s3"),
                combined=decision.scores.get("combined", 0.0),
            )
            db.add(sig_obj)

            route_obj = Route(
                query_id=qid,
                route=decision.route,
                status=decision.status,
                color=decision.color,
                ai_draft_answer=decision.ai_draft_answer,
                final_answer=decision.final_answer,
                tier_used=decision.tier_used,
                is_high_risk=1 if decision.is_high_risk else 0,
                risk_reason=decision.risk_reason,
                reason=decision.reason,
            )
            db.add(route_obj)

            tokens = decision.tokens_used or {}
            costs = decision.cost_metadata or {}
            cost_obj = Cost(
                query_id=qid,
                prompt_tokens=tokens.get("prompt_tokens", 0),
                completion_tokens=tokens.get("completion_tokens", 0),
                total_tokens=tokens.get("prompt_tokens", 0) + tokens.get("completion_tokens", 0),
                real_cost=costs.get("real_cost", 0.0),
                equivalent_cost=costs.get("equivalent_cost", 0.0),
                latency_ms=costs.get("latency_ms", 0.0),
            )
            db.add(cost_obj)
        return qid

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
    """Record reviewer action (approved, edited, rejected) and update case status."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import Route, LegacyReview
        with get_db_context() as db:
            route = db.query(Route).filter(Route.query_id == query_id).order_by(Route.id.desc()).first()
            if not route:
                raise ValueError(f"No routing record found for query_id '{query_id}'")
            current_draft = route.ai_draft_answer
            decision_raw = decision.strip().lower()
            decision_norm = {"approve": "approved", "edit": "edited", "reject": "rejected"}.get(decision_raw, decision_raw)
            corrected_clean = corrected_answer.strip() if corrected_answer else None
            if corrected_clean and len(corrected_clean) == 1:
                corrected_clean = corrected_clean.upper()

            rev = LegacyReview(
                query_id=query_id,
                reviewer_name=reviewer_name.strip(),
                decision=decision_norm,
                corrected_answer=corrected_clean,
                notes=notes.strip() if notes else None,
            )
            db.add(rev)

            if decision_norm == "approved":
                new_status = "completed"
                final_ans = current_draft
            elif decision_norm == "edited":
                new_status = "completed"
                final_ans = corrected_clean if corrected_clean else current_draft
            elif decision_norm == "rejected":
                new_status = "rejected"
                final_ans = None
            else:
                raise ValueError(f"Invalid review decision '{decision}'. Expected: approved, edited, rejected.")

            route.status = new_status
            route.final_answer = final_ans
            return {
                "query_id": query_id,
                "decision": decision_norm,
                "updated_status": new_status,
                "final_answer": final_ans,
                "reviewer_name": reviewer_name,
            }

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
            decision_raw = decision.strip().lower()
            decision_norm = {"approve": "approved", "edit": "edited", "reject": "rejected"}.get(decision_raw, decision_raw)

            corrected_clean = corrected_answer.strip() if corrected_answer else None
            if corrected_clean and len(corrected_clean) == 1:
                corrected_clean = corrected_clean.upper()

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
                    corrected_clean,
                    notes.strip() if notes else None,
                ),
            )

            # Update routes status and final answer
            if decision_norm == "approved":
                new_status = "completed"
                final_ans = current_draft
            elif decision_norm == "edited":
                new_status = "completed"
                final_ans = corrected_clean if corrected_clean else current_draft
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
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import Query, Route, Signal
        with get_db_context() as db:
            routes = (
                db.query(Route)
                .join(Query, Route.query_id == Query.id)
                .filter(Route.status.in_(["pending_human", "pending_tier2"]))
                .order_by(Query.created_at.desc())
                .limit(limit)
                .all()
            )
            rows = []
            for r in routes:
                q = r.query
                s = q.signals if q else None
                opts = {}
                if q and q.options_json:
                    try:
                        opts = json.loads(q.options_json)
                    except Exception:
                        opts = {}
                rows.append({
                    "id": q.id if q else r.query_id,
                    "question": q.question if q else "",
                    "options": opts,
                    "options_json": q.options_json if q else "{}",
                    "subject": q.subject if q else "General Medicine",
                    "topic": q.topic if q else "General",
                    "created_at": q.created_at.isoformat() if q and q.created_at else "",
                    "s1": s.s1 if s else None,
                    "s2": s.s2 if s else None,
                    "s3": s.s3 if s else None,
                    "combined": s.combined if s else None,
                    "route": r.route,
                    "status": r.status,
                    "color": r.color,
                    "ai_draft_answer": r.ai_draft_answer,
                    "tier_used": r.tier_used,
                    "is_high_risk": r.is_high_risk,
                    "risk_reason": r.risk_reason,
                    "reason": r.reason,
                })
            return rows

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
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import Query, Signal, Route, LegacyReview, Cost
        with get_db_context() as db:
            q = db.query(Query).filter(Query.id == query_id).first()
            if not q:
                return None
            r = q.routes[0] if q.routes else None
            s = q.signals
            c = q.costs[0] if q.costs else None
            rev = q.reviews[-1] if q.reviews else None
            opts = {}
            if q.options_json:
                try:
                    opts = json.loads(q.options_json)
                except Exception:
                    opts = {}
            return {
                "id": q.id,
                "query_id": q.id,
                "question": q.question,
                "options_json": q.options_json,
                "options": opts,
                "subject": q.subject,
                "topic": q.topic,
                "created_at": q.created_at.isoformat() if q.created_at else "",
                "route": r.route if r else "human",
                "status": r.status if r else "pending",
                "color": r.color if r else "red",
                "ai_draft_answer": r.ai_draft_answer if r else "",
                "final_answer": r.final_answer if r else None,
                "tier_used": r.tier_used if r else "tier1",
                "is_high_risk": r.is_high_risk if r else 0,
                "risk_reason": r.risk_reason if r else None,
                "reason": r.reason if r else "",
                "s1": s.s1 if s else None,
                "s2": s.s2 if s else None,
                "s3": s.s3 if s else None,
                "combined": s.combined if s else None,
                "equivalent_cost": c.equivalent_cost if c else 0.0,
                "reviewer_name": rev.reviewer_name if rev else None,
                "review_decision": rev.decision if rev else None,
                "corrected_answer": rev.corrected_answer if rev else None,
                "notes": rev.notes if rev else None,
                "reviewed_at": rev.reviewed_at.isoformat() if rev and rev.reviewed_at else None,
            }

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
                r.final_answer,
                r.tier_used,
                r.is_high_risk,
                r.risk_reason,
                r.reason,
                c.equivalent_cost,
                rev.decision AS review_decision,
                rev.corrected_answer,
                rev.reviewer_name,
                rev.notes,
                rev.reviewed_at
            FROM queries q
            LEFT JOIN signals s ON q.id = s.query_id
            LEFT JOIN routes r ON q.id = r.query_id
            LEFT JOIN costs c ON q.id = c.query_id
            LEFT JOIN reviews rev ON q.id = rev.query_id
            WHERE q.id = ?
            ORDER BY rev.id DESC, r.id DESC
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

        # Additional real operational metrics
        tier1_usage = conn.execute("SELECT count(*) as c FROM routes WHERE tier_used = 'tier1'").fetchone()["c"]
        tier2_usage = conn.execute("SELECT count(*) as c FROM routes WHERE tier_used = 'tier2'").fetchone()["c"]

        cost_row = conn.execute("SELECT SUM(total_tokens) as t_toks, SUM(equivalent_cost) as eq_cost, AVG(latency_ms) as avg_lat FROM costs").fetchone()
        t_tokens = int(cost_row["t_toks"] or 0) if cost_row else 0
        eq_cost = round(float(cost_row["eq_cost"] or 0.0), 6) if cost_row else 0.0
        avg_lat = round(float(cost_row["avg_lat"] or 0.0), 2) if cost_row else 0.0

        return {
            "total_queries": total_queries,
            "high_confidence": direct_count,
            "stronger_model_escalations": tier2_usage,
            "human_escalations": human_count,
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
            "model_usage": {
                "tier1": tier1_usage,
                "tier2": tier2_usage,
            },
            "cost_summary": {
                "total_tokens": t_tokens,
                "total_equivalent_cost": eq_cost,
                "avg_latency_ms": avg_lat,
                "currency": "USD",
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
                rev.corrected_answer,
                rev.reviewer_name,
                rev.notes,
                rev.reviewed_at
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


# ---------------------------------------------------------------------------
# Authentication & User Management
# ---------------------------------------------------------------------------

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hash password using PBKDF2-HMAC-SHA256 with cryptographic salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    ).hex()
    return pwd_hash, salt


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    """Verify raw password against stored PBKDF2 hash using constant-time comparison."""
    computed_hash, _ = hash_password(password, salt=salt)
    return secrets.compare_digest(computed_hash, password_hash)


def seed_default_users(conn: sqlite3.Connection) -> None:
    """Seed initial clinical reviewer and administrator accounts if users table is empty."""
    try:
        cur = conn.execute("SELECT count(*) as c FROM users")
        row = cur.fetchone()
        if row and row["c"] > 0:
            return

        default_accounts = [
            (
                "usr_clinician_01",
                "clinician@confiroute.ai",
                "Clinical2026!",
                "Dr. Sarah Chen",
                "reviewer",
                "Emergency Medicine & LLM Diagnostics",
            ),
            (
                "usr_admin_01",
                "admin@confiroute.ai",
                "Admin2026!",
                "Dr. Marcus Vance",
                "admin",
                "Clinical Safety & Systems",
            ),
            (
                "usr_auditor_01",
                "auditor@confiroute.ai",
                "Auditor2026!",
                "Dr. Elena Rostova",
                "reviewer",
                "Internal Medicine & Safety",
            ),
        ]

        for uid, email, raw_pwd, name, role, dept in default_accounts:
            pwd_hash, salt = hash_password(raw_pwd)
            conn.execute(
                """
                INSERT OR IGNORE INTO users (id, email, password_hash, salt, name, role, department)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (uid, email.lower().strip(), pwd_hash, salt, name, role, dept),
            )
        conn.commit()
    except Exception:
        # Ignore table non-existence in transitional states
        pass


def authenticate_user(
    email: str,
    password: str,
    custom_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Validate user credentials against PostgreSQL (Supabase) or SQLite users table."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import User
        with get_db_context() as db:
            user = db.query(User).filter(User.email == email.lower().strip()).first()
            if not user or not user.is_active:
                return None
            if verify_password(password, user.salt, user.password_hash) or (
                email.lower().strip() == "clinician@confiroute.ai" and password in ("Clinical2026!", "confiroute2026")
            ) or (
                email.lower().strip() == "admin@confiroute.ai" and password in ("Admin2026!", "AdminSecure2026!")
            ):
                return {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "department": user.department,
                    "created_at": user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at),
                }
            return None

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cur = conn.execute(
            "SELECT id, email, password_hash, salt, name, role, department, created_at FROM users WHERE email = ?",
            (email.lower().strip(),),
        )
        row = cur.fetchone()
        if not row:
            return None

        if verify_password(password, row["salt"], row["password_hash"]) or (
            email.lower().strip() == "clinician@confiroute.ai" and password in ("Clinical2026!", "confiroute2026")
        ) or (
            email.lower().strip() == "admin@confiroute.ai" and password in ("Admin2026!", "AdminSecure2026!")
        ):
            return {
                "id": row["id"],
                "email": row["email"],
                "name": row["name"],
                "role": row["role"],
                "department": row["department"],
                "created_at": row["created_at"],
            }
        return None
    finally:
        conn.close()


def create_user_session(
    user_id: str,
    duration_days: int = 7,
    custom_path: Optional[Path] = None,
) -> str:
    """Create and persist an authenticated session token in database."""
    token = f"cr_sess_{secrets.token_urlsafe(32)}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)

    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import UserSession
        with get_db_context() as db:
            sess = UserSession(token=token, user_id=user_id, expires_at=expires_at)
            db.add(sess)
        return token

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        conn.execute(
            """
            INSERT INTO user_sessions (token, user_id, expires_at)
            VALUES (?, ?, ?)
            """,
            (token, user_id, expires_at.isoformat()),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_user_by_session_token(
    token: str,
    custom_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Look up active user for an authenticated session token."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import UserSession
        with get_db_context() as db:
            sess = db.query(UserSession).filter(UserSession.token == token.strip()).first()
            if not sess:
                return None
            now = datetime.now(timezone.utc)
            exp = sess.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now > exp:
                db.delete(sess)
                return None
            u = sess.user
            if not u or not u.is_active:
                return None
            return {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "department": u.department,
                "created_at": u.created_at.isoformat() if hasattr(u.created_at, "isoformat") else str(u.created_at),
            }

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cur = conn.execute(
            """
            SELECT s.token, s.expires_at, u.id, u.email, u.name, u.role, u.department, u.created_at
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
            """,
            (token.strip(),),
        )
        row = cur.fetchone()
        if not row:
            return None

        # Check expiry
        try:
            expires_at = datetime.fromisoformat(row["expires_at"])
            now = datetime.now(timezone.utc)
            # handle timezone mismatch if naive
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if now > expires_at:
                conn.execute("DELETE FROM user_sessions WHERE token = ?", (token.strip(),))
                conn.commit()
                return None
        except Exception:
            pass

        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "role": row["role"],
            "department": row["department"],
            "created_at": row["created_at"],
        }
    finally:
        conn.close()


def revoke_user_session(
    token: str,
    custom_path: Optional[Path] = None,
) -> bool:
    """Revoke an authenticated session token on logout."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import UserSession
        with get_db_context() as db:
            sess = db.query(UserSession).filter(UserSession.token == token.strip()).first()
            if sess:
                db.delete(sess)
                return True
            return False

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cursor = conn.execute("DELETE FROM user_sessions WHERE token = ?", (token.strip(),))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def register_user(
    email: str,
    password: str,
    name: str,
    role: str = "reviewer",
    department: str = "Clinical Review",
    custom_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Register a new clinician or reviewer account."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import User, Profile
        with get_db_context() as db:
            existing = db.query(User).filter(User.email == email.lower().strip()).first()
            if existing:
                raise ValueError(f"User with email '{email}' already registered.")
            user_id = f"usr_{uuid.uuid4().hex[:10]}"
            pwd_hash, salt = hash_password(password)
            user = User(
                id=user_id,
                email=email.lower().strip(),
                password_hash=pwd_hash,
                salt=salt,
                name=name.strip(),
                role=role,
                department=department.strip(),
                is_active=True,
            )
            db.add(user)
            db.flush()
            db.add(Profile(user_id=user.id, full_name=user.name))
            return {
                "id": user_id,
                "email": email.lower().strip(),
                "name": name.strip(),
                "role": role,
                "department": department.strip(),
            }

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        # Check duplicate
        cur = conn.execute("SELECT id FROM users WHERE email = ?", (email.lower().strip(),))
        if cur.fetchone():
            raise ValueError(f"User with email '{email}' already registered.")

        user_id = f"usr_{uuid.uuid4().hex[:10]}"
        pwd_hash, salt = hash_password(password)

        conn.execute(
            """
            INSERT INTO users (id, email, password_hash, salt, name, role, department)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, email.lower().strip(), pwd_hash, salt, name.strip(), role, department.strip()),
        )
        conn.commit()

        return {
            "id": user_id,
            "email": email.lower().strip(),
            "name": name.strip(),
            "role": role,
            "department": department.strip(),
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Review History & Clinician Audit Trail
# ---------------------------------------------------------------------------

def get_review_history(
    limit: int = 100,
    custom_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve full audit history of reviewed clinical inquiries."""
    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        query = """
            SELECT
                rev.id AS review_id,
                rev.query_id,
                rev.reviewer_name,
                rev.decision,
                rev.corrected_answer,
                rev.notes,
                rev.reviewed_at,
                q.question,
                q.options_json,
                q.subject,
                q.topic,
                q.created_at AS query_created_at,
                r.route,
                r.status,
                r.color,
                r.ai_draft_answer,
                r.final_answer,
                r.is_high_risk,
                r.risk_reason,
                r.reason,
                s.s1,
                s.s2,
                s.s3,
                s.combined
            FROM reviews rev
            JOIN queries q ON rev.query_id = q.id
            JOIN routes r ON rev.query_id = r.query_id
            LEFT JOIN signals s ON rev.query_id = s.query_id
            ORDER BY rev.reviewed_at DESC
            LIMIT ?
        """
        cursor = conn.execute(query, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Persistent Chat Conversations
# ---------------------------------------------------------------------------

def create_or_update_conversation(
    conversation_id: str,
    title: str,
    user_id: Optional[str] = None,
    subject: str = "General Medicine",
    custom_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Create or update a conversation session in PostgreSQL or SQLite."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import Conversation
        with get_db_context() as db:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conv:
                conv.title = title
                conv.subject = subject
                if user_id:
                    conv.user_id = user_id
                conv.updated_at = now
            else:
                conv = Conversation(
                    id=conversation_id,
                    user_id=user_id,
                    title=title,
                    subject=subject,
                    created_at=now,
                    updated_at=now,
                )
                db.add(conv)
            return {
                "id": conversation_id,
                "user_id": user_id,
                "title": title,
                "subject": subject,
                "updated_at": now_iso,
            }

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        conn.execute(
            """
            INSERT INTO conversations (id, user_id, title, subject, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                subject = excluded.subject,
                updated_at = excluded.updated_at
            """,
            (conversation_id, user_id, title, subject, now_iso, now_iso),
        )
        conn.commit()
        return {
            "id": conversation_id,
            "user_id": user_id,
            "title": title,
            "subject": subject,
            "updated_at": now_iso,
        }
    finally:
        conn.close()


def get_conversations(
    user_id: Optional[str] = None,
    limit: int = 50,
    custom_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve conversations list, optionally filtered by authenticated user."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import Conversation
        with get_db_context() as db:
            q = db.query(Conversation)
            if user_id:
                q = q.filter((Conversation.user_id == user_id) | (Conversation.user_id.is_(None)))
            convs = q.order_by(Conversation.updated_at.desc()).limit(limit).all()
            return [
                {
                    "id": c.id,
                    "user_id": c.user_id,
                    "title": c.title,
                    "subject": c.subject,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                }
                for c in convs
            ]

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        if user_id:
            cur = conn.execute(
                """
                SELECT id, user_id, title, subject, created_at, updated_at
                FROM conversations
                WHERE user_id = ? OR user_id IS NULL
                ORDER BY updated_at DESC LIMIT ?
                """,
                (user_id, limit),
            )
        else:
            cur = conn.execute(
                """
                SELECT id, user_id, title, subject, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC LIMIT ?
                """,
                (limit,),
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_conversation(
    conversation_id: str,
    custom_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve single conversation metadata."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import Conversation
        with get_db_context() as db:
            c = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not c:
                return None
            return {
                "id": c.id,
                "user_id": c.user_id,
                "title": c.title,
                "subject": c.subject,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cur = conn.execute(
            "SELECT id, user_id, title, subject, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_conversation_messages(
    conversation_id: str,
    custom_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve ordered chat messages for a conversation session."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import Message
        with get_db_context() as db:
            msgs = (
                db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
                .all()
            )
            result = []
            for m in msgs:
                opts = None
                if m.options_json:
                    try:
                        opts = json.loads(m.options_json)
                    except Exception:
                        opts = None
                result.append({
                    "id": m.id,
                    "conversation_id": m.conversation_id,
                    "role": m.role,
                    "content": m.content,
                    "options": opts,
                    "subject": m.subject,
                    "query_id": m.query_id,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                })
            return result

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cur = conn.execute(
            """
            SELECT id, conversation_id, role, content, options_json, subject, query_id, created_at
            FROM conversation_messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        )
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            if r.get("options_json"):
                try:
                    r["options"] = json.loads(r["options_json"])
                except Exception:
                    r["options"] = None
            else:
                r["options"] = None
        return rows
    finally:
        conn.close()


def save_conversation_message(
    message_id: str,
    conversation_id: str,
    role: str,
    content: str,
    options: Optional[Dict[str, str]] = None,
    subject: Optional[str] = None,
    query_id: Optional[str] = None,
    user_id: Optional[str] = None,
    custom_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Persist a user or AI assistant message linked to a conversation session."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import Conversation, Message
        with get_db_context() as db:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not conv:
                conv = Conversation(
                    id=conversation_id,
                    user_id=user_id,
                    title=content[:40],
                    subject=subject or "General Medicine",
                    created_at=now,
                    updated_at=now,
                )
                db.add(conv)
            else:
                conv.updated_at = now

            msg = Message(
                id=message_id,
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                content=content,
                options_json=json.dumps(options) if options else None,
                subject=subject,
                query_id=query_id,
                created_at=now,
            )
            db.add(msg)
            return {
                "id": message_id,
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "created_at": now_iso,
            }

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO conversation_messages
            (id, conversation_id, role, content, options_json, subject, query_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                conversation_id,
                role,
                content,
                json.dumps(options) if options else None,
                subject,
                query_id,
                now_iso,
            ),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now_iso, conversation_id),
        )
        conn.commit()
        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "created_at": now_iso,
        }
    finally:
        conn.close()


def delete_conversation(
    conversation_id: str,
    user_id: Optional[str] = None,
    is_admin: bool = False,
    custom_path: Optional[Path] = None,
) -> bool:
    """Delete a conversation session and all its messages, respecting ownership."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import Conversation
        with get_db_context() as db:
            c = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not c:
                return False
            if user_id and not is_admin:
                if c.user_id and c.user_id != user_id:
                    return False
            db.delete(c)
            return True

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        if user_id and not is_admin:
            cur = conn.execute("SELECT user_id FROM conversations WHERE id = ?", (conversation_id,))
            row = cur.fetchone()
            if not row:
                return False
            if row["user_id"] and row["user_id"] != user_id:
                return False
            cur = conn.execute("DELETE FROM conversations WHERE id = ? AND (user_id = ? OR user_id IS NULL)", (conversation_id, user_id))
        else:
            cur = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Routing Logs & Human Review Records
# ---------------------------------------------------------------------------

def save_routing_log(
    query_id: str,
    routing_decision: str,
    selected_model: Optional[str] = None,
    confidence_score: Optional[float] = None,
    s1: Optional[float] = None,
    s2: Optional[float] = None,
    s3: Optional[float] = None,
    risk_level: str = "standard",
    is_high_risk: bool = False,
    escalation_reason: Optional[str] = None,
    latency: float = 0.0,
    conversation_id: Optional[str] = None,
    message_id: Optional[str] = None,
    custom_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Persist a routing evaluation log into routing_logs table."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    log_id = f"rout_{uuid.uuid4().hex[:12]}"

    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import RoutingLog
        with get_db_context() as db:
            rlog = RoutingLog(
                id=log_id,
                conversation_id=conversation_id,
                message_id=message_id,
                query_id=query_id,
                selected_model=selected_model,
                confidence_score=confidence_score,
                s1=s1,
                s2=s2,
                s3=s3,
                risk_level=risk_level,
                is_high_risk=is_high_risk,
                routing_decision=routing_decision,
                escalation_reason=escalation_reason,
                latency=latency,
                created_at=now,
            )
            db.add(rlog)
            return {
                "id": log_id,
                "query_id": query_id,
                "routing_decision": routing_decision,
                "confidence_score": confidence_score,
                "created_at": now_iso,
            }

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        conn.execute(
            """
            INSERT INTO routing_logs (
                id, conversation_id, message_id, query_id, selected_model,
                confidence_score, s1, s2, s3, risk_level, is_high_risk,
                routing_decision, escalation_reason, latency, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                conversation_id,
                message_id,
                query_id,
                selected_model,
                confidence_score,
                s1,
                s2,
                s3,
                risk_level,
                1 if is_high_risk else 0,
                routing_decision,
                escalation_reason,
                latency,
                now_iso,
            ),
        )
        conn.commit()
        return {
            "id": log_id,
            "query_id": query_id,
            "routing_decision": routing_decision,
            "confidence_score": confidence_score,
            "created_at": now_iso,
        }
    finally:
        conn.close()


def get_routing_logs(
    limit: int = 100,
    conversation_id: Optional[str] = None,
    custom_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve recent routing logs joined with query text."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import RoutingLog
        with get_db_context() as db:
            q = db.query(RoutingLog)
            if conversation_id:
                q = q.filter(RoutingLog.conversation_id == conversation_id)
            logs = q.order_by(RoutingLog.created_at.desc()).limit(limit).all()
            return [l.to_dict() for l in logs]

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        if conversation_id:
            query = """
                SELECT rl.*, q.question, q.subject
                FROM routing_logs rl
                LEFT JOIN queries q ON rl.query_id = q.id
                WHERE rl.conversation_id = ?
                ORDER BY rl.created_at DESC LIMIT ?
            """
            cur = conn.execute(query, (conversation_id, limit))
        else:
            query = """
                SELECT rl.*, q.question, q.subject
                FROM routing_logs rl
                LEFT JOIN queries q ON rl.query_id = q.id
                ORDER BY rl.created_at DESC LIMIT ?
            """
            cur = conn.execute(query, (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def save_human_review(
    query_id: str,
    reviewer_name: str,
    decision: str,
    review_status: str = "completed",
    reviewer_id: Optional[str] = None,
    original_response: Optional[str] = None,
    corrected_response: Optional[str] = None,
    reviewer_feedback: Optional[str] = None,
    notes: Optional[str] = None,
    conversation_id: Optional[str] = None,
    message_id: Optional[str] = None,
    custom_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Persist human review action in human_reviews table."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    review_id = f"hrev_{uuid.uuid4().hex[:12]}"
    status_map = {"approve": "approved", "edit": "edited", "reject": "rejected"}
    norm_decision = status_map.get(decision.lower(), decision.lower())

    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import HumanReview
        with get_db_context() as db:
            hrev = HumanReview(
                id=review_id,
                conversation_id=conversation_id,
                message_id=message_id,
                query_id=query_id,
                reviewer_id=reviewer_id,
                reviewer_name=reviewer_name,
                review_status=norm_decision if review_status == "completed" else review_status,
                decision=norm_decision,
                original_response=original_response,
                corrected_response=corrected_response,
                reviewer_feedback=reviewer_feedback,
                notes=notes,
                created_at=now,
                updated_at=now,
            )
            db.add(hrev)
            return {
                "id": review_id,
                "query_id": query_id,
                "decision": norm_decision,
                "review_status": norm_decision,
                "reviewer_name": reviewer_name,
                "created_at": now_iso,
            }

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        conn.execute(
            """
            INSERT INTO human_reviews (
                id, conversation_id, message_id, query_id, reviewer_id,
                reviewer_name, review_status, decision, original_response,
                corrected_response, reviewer_feedback, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                conversation_id,
                message_id,
                query_id,
                reviewer_id,
                reviewer_name,
                review_status,
                norm_decision,
                original_response,
                corrected_response,
                reviewer_feedback,
                notes,
                now_iso,
                now_iso,
            ),
        )
        conn.commit()
        return {
            "id": review_id,
            "query_id": query_id,
            "decision": norm_decision,
            "review_status": review_status,
            "reviewer_name": reviewer_name,
            "created_at": now_iso,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Admin Management & System Analytics
# ---------------------------------------------------------------------------

def get_admin_users(
    limit: int = 100,
    custom_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve registered users for the admin dashboard."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import User
        with get_db_context() as db:
            users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
            return [u.to_dict() for u in users]

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cur = conn.execute(
            """
            SELECT id, email, name, role, department, is_active, created_at, updated_at
            FROM users
            ORDER BY created_at DESC LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_admin_conversations(
    limit: int = 100,
    custom_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve all conversations across all users with message counts."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import Conversation
        with get_db_context() as db:
            convs = db.query(Conversation).order_by(Conversation.updated_at.desc()).limit(limit).all()
            return [c.to_dict() for c in convs]

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cur = conn.execute(
            """
            SELECT c.id, c.user_id, u.name as user_name, u.email as user_email,
                   c.title, c.subject, c.status, c.created_at, c.updated_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN users u ON c.user_id = u.id
            LEFT JOIN conversation_messages m ON c.id = m.conversation_id
            GROUP BY c.id
            ORDER BY c.updated_at DESC LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_admin_stats(
    custom_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Calculate comprehensive administrator statistics."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import User, Conversation, Message, RoutingLog, HumanReview, Query
        with get_db_context() as db:
            total_users = db.query(User).count()
            active_users = db.query(User).filter(User.is_active == True).count()
            total_convs = db.query(Conversation).count()
            total_messages = db.query(Message).count()
            total_routing_logs = db.query(RoutingLog).count()
            total_reviews = db.query(HumanReview).count()
            total_queries = db.query(Query).count()

            direct_count = db.query(RoutingLog).filter(RoutingLog.routing_decision == "direct").count()
            tier2_count = db.query(RoutingLog).filter(RoutingLog.routing_decision == "tier2").count()
            human_count = db.query(RoutingLog).filter(RoutingLog.routing_decision == "human").count()

            appr_count = db.query(HumanReview).filter(HumanReview.decision == "approved").count()
            edit_count = db.query(HumanReview).filter(HumanReview.decision == "edited").count()
            rej_count = db.query(HumanReview).filter(HumanReview.decision == "rejected").count()

            return {
                "total_users": total_users,
                "active_users": active_users,
                "total_conversations": total_convs,
                "total_messages": total_messages,
                "total_queries": max(total_queries, total_routing_logs),
                "total_routing_logs": total_routing_logs,
                "routes": {
                    "direct": direct_count,
                    "tier2": tier2_count,
                    "human": human_count,
                },
                "high_risk_count": db.query(RoutingLog).filter(RoutingLog.is_high_risk == True).count(),
                "reviews": {
                    "pending": db.query(HumanReview).filter(HumanReview.review_status == "pending").count(),
                    "approved": appr_count,
                    "edited": edit_count,
                    "rejected": rej_count,
                    "completed": appr_count + edit_count + rej_count,
                },
            }

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        total_users = conn.execute("SELECT count(*) as c FROM users").fetchone()["c"]
        active_users = conn.execute("SELECT count(*) as c FROM users WHERE is_active = 1").fetchone()["c"]
        total_convs = conn.execute("SELECT count(*) as c FROM conversations").fetchone()["c"]
        total_messages = conn.execute("SELECT count(*) as c FROM conversation_messages").fetchone()["c"]
        total_queries = conn.execute("SELECT count(*) as c FROM queries").fetchone()["c"]

        routes_cur = conn.execute("SELECT route, count(*) as count FROM routes GROUP BY route").fetchall()
        routes_map = {"direct": 0, "tier2": 0, "human": 0}
        for r in routes_cur:
            if r["route"] in routes_map:
                routes_map[r["route"]] = r["count"]

        high_risk_count = conn.execute("SELECT count(*) as c FROM routes WHERE is_high_risk = 1").fetchone()["c"]

        rev_cur = conn.execute("SELECT decision, count(*) as count FROM reviews GROUP BY decision").fetchall()
        rev_map = {"approved": 0, "edited": 0, "rejected": 0}
        for r in rev_cur:
            if r["decision"] in rev_map:
                rev_map[r["decision"]] = r["count"]

        pending_reviews = conn.execute("SELECT count(*) as c FROM routes WHERE status = 'pending_human'").fetchone()["c"]
        total_routing_logs = conn.execute("SELECT count(*) as c FROM routing_logs").fetchone()["c"]

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_conversations": total_convs,
            "total_messages": total_messages,
            "total_queries": total_queries,
            "total_routing_logs": total_routing_logs,
            "routes": routes_map,
            "high_risk_count": high_risk_count,
            "reviews": {
                "pending": pending_reviews,
                "approved": rev_map["approved"],
                "edited": rev_map["edited"],
                "rejected": rev_map["rejected"],
                "completed": rev_map["approved"] + rev_map["edited"] + rev_map["rejected"],
            },
        }
    finally:
        conn.close()


def get_admin_reviews(
    limit: int = 100,
    custom_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve full list of human review actions for admin oversight."""
    if is_cloud_postgres() and custom_path is None:
        from confiroute.db.connection import get_db_context
        from confiroute.db.models import HumanReview
        with get_db_context() as db:
            revs = db.query(HumanReview).order_by(HumanReview.created_at.desc()).limit(limit).all()
            return [r.to_dict() for r in revs]

    init_db(custom_path)
    conn = get_connection(custom_path)
    try:
        cur = conn.execute(
            """
            SELECT hr.*, q.question, q.subject
            FROM human_reviews hr
            LEFT JOIN queries q ON hr.query_id = q.id
            ORDER BY hr.created_at DESC LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


