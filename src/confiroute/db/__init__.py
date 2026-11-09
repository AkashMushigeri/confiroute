"""Database persistence and schema helpers for ConfiRoute."""

from confiroute.db.database import (
    init_db,
    get_connection,
    get_db_path,
    save_pipeline_execution,
    get_recent_history,
    record_review_decision,
    get_pending_reviews,
    get_resolved_reviews,
    get_query_result,
    get_system_stats,
    insert_alert,
    get_active_alerts,
    has_recent_alert_of_type,
    clear_alerts,
    get_dashboard_query_records,
)

__all__ = [
    "init_db",
    "get_connection",
    "get_db_path",
    "save_pipeline_execution",
    "get_recent_history",
    "record_review_decision",
    "get_pending_reviews",
    "get_resolved_reviews",
    "get_query_result",
    "get_system_stats",
    "insert_alert",
    "get_active_alerts",
    "has_recent_alert_of_type",
    "clear_alerts",
    "get_dashboard_query_records",
]
