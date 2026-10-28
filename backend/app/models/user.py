from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.roles import Role


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default=Role.CITIZEN.value, nullable=False, index=True)
    assigned_district_id = Column(Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_state_id = Column(Integer, ForeignKey("states.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    assigned_district = relationship("District", back_populates="officers", foreign_keys=[assigned_district_id])
    assigned_state = relationship("State", foreign_keys=[assigned_state_id])
    reports = relationship("CitizenReport", back_populates="user", foreign_keys="CitizenReport.user_id")
    assigned_reports = relationship("CitizenReport", back_populates="assigned_officer", foreign_keys="CitizenReport.assigned_officer_id")
    reviews = relationship("ReportReview", back_populates="reviewer")
    authored_alerts = relationship("Alert", back_populates="created_by_user")

    @property
    def normalized_role(self) -> Role:
        return Role.normalize(self.role)
