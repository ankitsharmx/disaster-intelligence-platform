from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(150), nullable=False, index=True)  # user email or system process name
    action = Column(String(100), nullable=False, index=True)  # e.g., create_alert, verify_report, replay_event
    affected_record = Column(String(100), nullable=False, index=True)  # e.g., Alert:12, CitizenReport:45
    details = Column(JSON, nullable=True)  # payload or before/after diff
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
