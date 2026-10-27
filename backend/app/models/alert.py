from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False, index=True)  # flood, cyclone, earthquake, fire, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    issuer = Column(String(100), nullable=False, index=True)  # State Disaster Mgmt, District Collector, etc.
    valid_from = Column(DateTime(timezone=True), nullable=False, index=True)
    valid_to = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(20), default="active", nullable=False, index=True)  # active, draft, expired, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    areas = relationship("AlertArea", back_populates="alert", cascade="all, delete-orphan")


class AlertArea(Base):
    __tablename__ = "alert_areas"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True)
    boundary = Column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
    boundary_geojson = Column(JSON, nullable=True)

    # Relationships
    alert = relationship("Alert", back_populates="areas")
    district = relationship("District")
