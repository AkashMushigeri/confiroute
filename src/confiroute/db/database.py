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
