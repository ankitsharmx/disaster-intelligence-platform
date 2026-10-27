from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.db.base import Base


class HazardObservation(Base):
    __tablename__ = "hazard_observations"

    id = Column(Integer, primary_key=True, index=True)
    hazard_type = Column(String(50), nullable=False, index=True)  # rainfall, flood, earthquake, fire, cyclone
    values = Column(JSON, nullable=False)  # e.g., {"rainfall_mm": 110.5, "unit": "mm"}
    observed_time = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(100), nullable=False, index=True)  # imd, usgs, demo, etc.
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True)
    location = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    district = relationship("District", back_populates="hazard_observations")


class DataSourceRun(Base):
    __tablename__ = "data_source_runs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False, index=True)  # e.g., weather_source, usgs_source
    mode = Column(String(20), nullable=False, index=True)  # demo, live
    status = Column(String(20), nullable=False, index=True)  # success, failed, running
    retrieval_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    records_count = Column(Integer, default=0, nullable=False)
    error = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
