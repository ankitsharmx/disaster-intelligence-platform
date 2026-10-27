from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class AwarenessContent(Base):
    __tablename__ = "awareness_contents"

    id = Column(Integer, primary_key=True, index=True)
    hazard = Column(String(50), nullable=False, index=True)  # flood, earthquake, cyclone, fire
    stage = Column(String(20), nullable=False, index=True)  # before, during, after
    language = Column(String(10), default="en", nullable=False, index=True)
    title = Column(String(255), nullable=False)
    instructions = Column(JSON, nullable=False)  # List of steps/tips or structured recommendations
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
