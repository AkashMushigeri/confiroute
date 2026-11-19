"""SQLAlchemy ORM models for ConfiRoute.

Supports both PostgreSQL (Supabase) and SQLite with full schema compatibility.
Tables:
- users
- profiles
- user_sessions
- conversations
- messages (conversation_messages)
- routing_logs
- human_reviews (reviews)
- audit_logs
- queries
- signals
- routes
- costs
- alerts
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid(prefix: str = "") -> str:
    short_id = uuid.uuid4().hex[:12]
    return f"{prefix}{short_id}" if prefix else short_id


# ---------------------------------------------------------------------------
# Core User & Auth Models
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=lambda: generate_uuid("usr_"))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    role = Column(String(32), nullable=False, default="reviewer")  # admin, reviewer, clinician
    department = Column(String(128), default="Clinical Review")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user")
    reviews = relationship("HumanReview", back_populates="reviewer")
    audit_logs = relationship("AuditLog", back_populates="user")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "department": self.department,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String(64), primary_key=True, default=lambda: generate_uuid("prf_"))
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)
    profile_image = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="profile")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "profile_image": self.profile_image,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserSession(Base):
    __tablename__ = "user_sessions"

    token = Column(String(128), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="sessions")


# ---------------------------------------------------------------------------
# Conversations & Messages Models
# ---------------------------------------------------------------------------

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True, default=lambda: generate_uuid("conv_"))
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False, default="Clinical Inquiry")
    subject = Column(String(128), default="General Medicine")
    status = Column(String(32), default="active", nullable=False)  # active, archived
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    routing_logs = relationship("RoutingLog", back_populates="conversation")
    human_reviews = relationship("HumanReview", back_populates="conversation")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else None,
            "user_email": self.user.email if self.user else None,
            "title": self.title,
            "subject": self.subject,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "message_count": len(self.messages) if self.messages else 0,
        }


class Message(Base):
    __tablename__ = "conversation_messages"

    id = Column(String(64), primary_key=True, default=lambda: generate_uuid("msg_"))
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    role = Column(String(32), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    options_json = Column(Text, nullable=True)
    subject = Column(String(128), nullable=True)
    query_id = Column(String(64), ForeignKey("queries.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
    query = relationship("Query", back_populates="messages")
    routing_logs = relationship("RoutingLog", back_populates="message")
    human_reviews = relationship("HumanReview", back_populates="message")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "options_json": self.options_json,
            "subject": self.subject,
            "query_id": self.query_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Routing Logs & Human Reviews Models
# ---------------------------------------------------------------------------

class RoutingLog(Base):
    __tablename__ = "routing_logs"

    id = Column(String(64), primary_key=True, default=lambda: generate_uuid("rout_"))
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    message_id = Column(String(64), ForeignKey("conversation_messages.id", ondelete="SET NULL"), nullable=True, index=True)
    query_id = Column(String(64), ForeignKey("queries.id", ondelete="SET NULL"), nullable=True, index=True)
    selected_model = Column(String(128), nullable=True)  # llama3.2:3b, gpt-oss-120b, etc.
    confidence_score = Column(Float, nullable=True)
    s1 = Column(Float, nullable=True)
    s2 = Column(Float, nullable=True)
    s3 = Column(Float, nullable=True)
    risk_level = Column(String(32), default="standard")  # standard, high
    is_high_risk = Column(Boolean, default=False)
    routing_decision = Column(String(32), nullable=False)  # direct, tier2, human
    escalation_reason = Column(Text, nullable=True)
    latency = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    conversation = relationship("Conversation", back_populates="routing_logs")
    message = relationship("Message", back_populates="routing_logs")
    query = relationship("Query", back_populates="routing_logs")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "query_id": self.query_id,
            "selected_model": self.selected_model,
            "confidence_score": self.confidence_score,
            "s1": self.s1,
            "s2": self.s2,
            "s3": self.s3,
            "risk_level": self.risk_level,
            "is_high_risk": self.is_high_risk,
            "routing_decision": self.routing_decision,
            "escalation_reason": self.escalation_reason,
            "latency": self.latency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id = Column(String(64), primary_key=True, default=lambda: generate_uuid("hrev_"))
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    message_id = Column(String(64), ForeignKey("conversation_messages.id", ondelete="SET NULL"), nullable=True, index=True)
    query_id = Column(String(64), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewer_name = Column(String(255), nullable=True)
    review_status = Column(String(32), default="pending", nullable=False)  # pending, approved, edited, rejected
    decision = Column(String(32), nullable=True)
    original_response = Column(Text, nullable=True)
    corrected_response = Column(Text, nullable=True)
    reviewer_feedback = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="human_reviews")
    message = relationship("Message", back_populates="human_reviews")
    query = relationship("Query", back_populates="human_reviews")
    reviewer = relationship("User", back_populates="reviews")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "query_id": self.query_id,
            "reviewer_id": self.reviewer_id,
            "reviewer_name": self.reviewer_name,
            "review_status": self.review_status,
            "decision": self.decision,
            "original_response": self.original_response,
            "corrected_response": self.corrected_response,
            "reviewer_feedback": self.reviewer_feedback,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True, default=lambda: generate_uuid("aud_"))
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(64), nullable=False)  # user_login, conversation_delete, review_submit, etc.
    resource_type = Column(String(64), nullable=False)  # conversation, review, user, auth
    resource_id = Column(String(64), nullable=True)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details_json": self.details_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Legacy Table Compatibility (queries, signals, routes, reviews, costs, alerts)
# ---------------------------------------------------------------------------

class Query(Base):
    __tablename__ = "queries"

    id = Column(String(64), primary_key=True)
    question = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    correct_letter = Column(String(8), nullable=True)
    subject = Column(String(128), default="General Medicine")
    topic = Column(String(128), default="General")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    messages = relationship("Message", back_populates="query")
    routing_logs = relationship("RoutingLog", back_populates="query")
    human_reviews = relationship("HumanReview", back_populates="query")
    signals = relationship("Signal", back_populates="query", uselist=False, cascade="all, delete-orphan")
    routes = relationship("Route", back_populates="query", cascade="all, delete-orphan")
    reviews = relationship("LegacyReview", back_populates="query", cascade="all, delete-orphan")
    costs = relationship("Cost", back_populates="query", cascade="all, delete-orphan")


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(64), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    s1 = Column(Float, nullable=True)
    s2 = Column(Float, nullable=True)
    s3 = Column(Float, nullable=True)
    combined = Column(Float, nullable=False)
    mean_logprob = Column(Float, nullable=True)
    agreement_stats_json = Column(Text, nullable=True)
    effective_weights_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    query = relationship("Query", back_populates="signals")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(64), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    route = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)
    color = Column(String(32), nullable=False)
    ai_draft_answer = Column(Text, nullable=True)
    final_answer = Column(Text, nullable=True)
    tier_used = Column(String(64), nullable=True)
    is_high_risk = Column(Integer, nullable=False, default=0)
    risk_reason = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    query = relationship("Query", back_populates="routes")


class LegacyReview(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(64), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_name = Column(String(255), nullable=True)
    decision = Column(String(32), nullable=True)
    corrected_answer = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), default=utcnow)

    query = relationship("Query", back_populates="reviews")


class Cost(Base):
    __tablename__ = "costs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(64), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    real_cost = Column(Float, default=0.0)
    equivalent_cost = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    query = relationship("Query", back_populates="costs")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(64), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(32), default="warning")
    created_at = Column(DateTime(timezone=True), default=utcnow)
