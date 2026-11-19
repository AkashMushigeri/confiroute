"""Audit logging utilities for tracking security, routing, and administrative actions."""

import json
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from confiroute.db.models import AuditLog, generate_uuid


def record_audit_log(
    db: Session,
    action: str,
    resource_type: str,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Record an audit trail entry for security, review, or administrative operations."""
    entry = AuditLog(
        id=generate_uuid("aud_"),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details_json=json.dumps(details) if details else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
