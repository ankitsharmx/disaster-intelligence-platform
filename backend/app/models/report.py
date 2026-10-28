from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.db.base import Base


class ReportStatus:
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    RESOLVED = "resolved"

    @classmethod
    def all_statuses(cls):
        return {cls.SUBMITTED, cls.UNDER_REVIEW, cls.VERIFIED, cls.REJECTED, cls.RESOLVED}

    @classmethod
    def public_visible_statuses(cls):
        """Only verified incident reports may be viewed by the public."""
        return {cls.VERIFIED}


class CitizenReport(Base):
    __tablename__ = "citizen_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_officer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(String(50), nullable=False, index=True)  # flood, waterlogging, landslide, etc.
    description = Column(Text, nullable=False)
    location = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String(30), default=ReportStatus.SUBMITTED, nullable=False, index=True)
    confidence_score = Column(Float, default=1.0, nullable=False)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    duplicate_of_id = Column(Integer, ForeignKey("citizen_reports.id", ondelete="SET NULL"), nullable=True)
    reopened_count = Column(Integer, default=0, nullable=False)
    reopened_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships with eager selectin loading for async FastAPI serialization
    user = relationship("User", back_populates="reports", foreign_keys=[user_id], lazy="selectin")
    assigned_officer = relationship("User", back_populates="assigned_reports", foreign_keys=[assigned_officer_id], lazy="selectin")
    district = relationship("District", back_populates="reports", lazy="selectin")
    media = relationship("ReportMedia", back_populates="report", cascade="all, delete-orphan", lazy="selectin")
    reviews = relationship("ReportReview", back_populates="report", cascade="all, delete-orphan", lazy="selectin")
    duplicates = relationship("CitizenReport", backref="original_report", remote_side=[id])


class ReportMedia(Base):
    __tablename__ = "report_media"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("citizen_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    content_type = Column(String(100), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    report = relationship("CitizenReport", back_populates="media")


class ReportReview(Base):
    __tablename__ = "report_reviews"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("citizen_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    decision = Column(String(30), nullable=False)  # verified, rejected, resolved, escalated
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    report = relationship("CitizenReport", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews", lazy="selectin")
