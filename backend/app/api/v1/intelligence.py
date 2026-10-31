from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.hazard import HazardObservation
from app.models.geography import District
from app.models.report import CitizenReport, ReportStatus
from app.intelligence.flood_risk import FloodRiskEngine
from app.intelligence.landslide_risk import LandslideRiskEngine
from app.intelligence.flood_ml_service import flood_ml_service
from app.intelligence.landslide_ml_service import landslide_ml_service
from app.intelligence.feature_extraction import FeatureExtractor
from app.intelligence.duplicate_detection import duplicate_detector
from app.intelligence.report_confidence import ReportConfidenceScorer
from app.intelligence.ml_baseline import ml_baseline

router = APIRouter(prefix="/intelligence", tags=["Intelligence & Risk Engine"])


class ConfidenceEvaluationRequest(BaseModel):
    description: str = Field(..., min_length=3, description="Incident report text description")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    has_media: bool = Field(False, description="Whether photographic evidence is attached")
    user_role: str = Field("citizen", description="Role of the submitter")
    corroborating_reports_count: int = Field(0, ge=0)
    nearby_sensor_active: bool = Field(False)
    rainfall_observed_mm: Optional[float] = None
    hazard_type: str = Field("flood", description="flood, landslide, fire, etc.")


class DuplicateClusterRequest(BaseModel):
    district_id: Optional[int] = Field(None, description="District to cluster active reports from")
    max_distance_meters: float = Field(500.0, ge=50, le=5000)
    max_time_delta_seconds: float = Field(7200.0, ge=300, le=86400)


@router.get("/risk/flood")
async def get_indicative_flood_risk(
    district_id: Optional[int] = Query(None, description="District ID"),
    rainfall_1h_mm: Optional[float] = Query(None, ge=0),
    rainfall_24h_mm: Optional[float] = Query(None, ge=0),
    water_level_m: Optional[float] = Query(None, ge=0),
    danger_mark_m: Optional[float] = Query(None, ge=0),
    engine: str = Query("rules", description="Inference engine: 'rules' (deterministic IMD/CWC) or 'ml' (trained pipeline)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes structured indicative flood risk assessment.
    Supports:
    - engine='ml': Trained HistGradientBoosting / Random Forest ML Pipeline (predicts 72h onset probability)
    - engine='rules': IMD & CWC deterministic sensor rule thresholds
    Output is strictly labeled: 'Indicative risk — not an official warning.'
    """
    observations: Dict[str, Any] = {}

    # If query parameters are provided, use them directly
    if rainfall_1h_mm is not None or water_level_m is not None:
        if rainfall_1h_mm is not None:
            observations["rainfall"] = {
                "values": {
                    "rainfall_1h_mm": rainfall_1h_mm,
                    "rainfall_24h_mm": rainfall_24h_mm or (rainfall_1h_mm * 4.0),
                }
            }
        if water_level_m is not None:
            observations["flood"] = {
                "values": {
                    "water_level_meters": water_level_m,
                    "danger_mark_meters": danger_mark_m or 4.5,
                }
            }
    elif district_id:
        # Pull latest observations from database for this district
        q = (
            select(HazardObservation)
            .filter((HazardObservation.district_id == district_id) | (HazardObservation.district_id.is_(None)))
            .order_by(HazardObservation.observed_time.desc())
            .limit(10)
        )
        res = await db.execute(q)
        for obs in res.scalars().all():
            if obs.hazard_type not in observations:
                observations[obs.hazard_type] = {"values": obs.values}

    if engine == "rules":
        return FloodRiskEngine.calculate_risk(observations=observations, district_id=district_id)
    else:
        return flood_ml_service.predict(district_id=district_id, observations=observations)


@router.get("/risk/landslide")
async def get_indicative_landslide_risk(
    district_id: Optional[int] = Query(None, description="District ID"),
    rainfall_72h_mm: Optional[float] = Query(None, ge=0),
    rainfall_24h_mm: Optional[float] = Query(None, ge=0),
    avg_slope_deg: Optional[float] = Query(None, ge=0, le=90),
    engine: str = Query("rules", description="Inference engine: 'rules' (deterministic GSI) or 'ml' (Random Forest + GSI criteria)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes structured indicative landslide risk assessment.
    Supports:
    - engine='ml': Calibrated Random Forest susceptibility coupled with dynamic GSI rainfall triggering
    - engine='rules': Purely deterministic rule thresholds
    Output is strictly labeled: 'Indicative risk — not an official warning.'
    """
    observations: Dict[str, Any] = {}

    if rainfall_72h_mm is not None or rainfall_24h_mm is not None:
        observations["rainfall"] = {
            "values": {
                "rainfall_72h_mm": rainfall_72h_mm or (rainfall_24h_mm * 2.0 if rainfall_24h_mm else 0.0),
                "rainfall_24h_mm": rainfall_24h_mm or 0.0,
            }
        }
    elif district_id:
        q = (
            select(HazardObservation)
            .filter((HazardObservation.district_id == district_id) | (HazardObservation.district_id.is_(None)))
            .order_by(HazardObservation.observed_time.desc())
            .limit(10)
        )
        res = await db.execute(q)
        for obs in res.scalars().all():
            if obs.hazard_type not in observations:
                observations[obs.hazard_type] = {"values": obs.values}

    if engine == "rules":
        return LandslideRiskEngine.calculate_risk(observations=observations, district_id=district_id)
    else:
        return landslide_ml_service.predict(
            district_id=district_id,
            slope_deg=avg_slope_deg,
            observations=observations
        )


@router.get("/risk/district/{district_id}")
async def get_district_multi_hazard_risk(
    district_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Synthesizes multi-hazard indicative risk assessments (Flood, Landslide) for an administrative district.
    Integrates terrain profile, soil saturation, and latest hydrometeorological observations.
    """
    d_res = await db.execute(select(District).filter(District.id == district_id))
    district = d_res.scalar_one_or_none()
    if not district:
        raise HTTPException(status_code=404, detail="District not found")

    # Fetch latest observations
    q = (
        select(HazardObservation)
        .filter((HazardObservation.district_id == district_id) | (HazardObservation.district_id.is_(None)))
        .order_by(HazardObservation.observed_time.desc())
        .limit(20)
    )
    res = await db.execute(q)
    observations: Dict[str, Any] = {}
    for obs in res.scalars().all():
        if obs.hazard_type not in observations:
            observations[obs.hazard_type] = {"values": obs.values}

    flood_eval = FloodRiskEngine.calculate_risk(observations, district_id=district_id)
    landslide_eval = LandslideRiskEngine.calculate_risk(observations, district_id=district_id)
    features = FeatureExtractor.extract_environmental_features(observations, district_id=district_id)

    # Production Trained ML Models (Model 1: Flood 72h onset, Model 2: Landslide Susceptibility + GSI Trigger)
    ml_flood = flood_ml_service.predict(district_id=district_id, district_name=district.name, observations=observations)
    ml_landslide = landslide_ml_service.predict(district_id=district_id, district_name=district.name, observations=observations)

    # ML comparative prediction
    ml_eval = ml_baseline.predict_risk(features)

    # Highest indicative severity
    sev_ranks = {"LOW": 1, "MEDIUM": 2, "MODERATE": 2, "HIGH": 3, "CRITICAL": 4}
    f_rank = sev_ranks.get(flood_eval.get("riskLevel", "LOW"), 1)
    l_rank = sev_ranks.get(landslide_eval.get("riskLevel", "LOW"), 1)
    composite_level = flood_eval.get("riskLevel", "LOW") if f_rank >= l_rank else landslide_eval.get("riskLevel", "LOW")

    return {
        "district": {
            "id": district.id,
            "name": district.name,
            "code": district.code,
        },
        "indicative_disclaimer": "Indicative risk — not an official warning.",
        "composite_risk_level": composite_level,
        "isOfficialWarning": False,
        "hazards": {
            "flood": flood_eval,
            "landslide": landslide_eval,
        },
        "ml_predictions": {
            "flood": ml_flood,
            "landslide": ml_landslide,
        },
        "ml_comparative_baseline": ml_eval,
        "environmental_features": features,
    }


@router.post("/confidence/evaluate")
async def evaluate_report_confidence(
    payload: ConfidenceEvaluationRequest,
):
    """
    Evaluates explainable multi-signal confidence score for a hazard report.
    Returns LOW, MEDIUM, or HIGH confidence with itemized contributing factors.
    Missing data does not imply false report; output is advisory.
    """
    return ReportConfidenceScorer.evaluate_confidence(
        description=payload.description,
        latitude=payload.latitude,
        longitude=payload.longitude,
        has_media=payload.has_media,
        user_role=payload.user_role,
        corroborating_reports_count=payload.corroborating_reports_count,
        nearby_sensor_active=payload.nearby_sensor_active,
        rainfall_observed_mm=payload.rainfall_observed_mm,
        hazard_type=payload.hazard_type,
    )


@router.post("/duplicates/cluster")
async def cluster_duplicate_reports(
    payload: DuplicateClusterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Groups nearby reports by distance, elapsed time, and TF-IDF text similarity.
    Returns cluster groups for officer review queue. Suspected duplicates are NOT auto-deleted.
    """
    q = select(CitizenReport).filter(
        CitizenReport.status.in_([ReportStatus.SUBMITTED, ReportStatus.UNDER_REVIEW])
    )
    if payload.district_id:
        q = q.filter(CitizenReport.district_id == payload.district_id)
    q = q.order_by(CitizenReport.created_at.desc()).limit(150)

    res = await db.execute(q)
    reports_orm = res.scalars().all()

    report_dicts = [
        {
            "id": r.id,
            "type": r.type,
            "description": r.description,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in reports_orm
    ]

    clusters = duplicate_detector.cluster_reports(
        reports=report_dicts,
        distance_threshold_m=payload.max_distance_meters,
        time_threshold_sec=payload.max_time_delta_seconds,
    )

    duplicate_clusters = [c for c in clusters if c["is_duplicate_group"]]

    return {
        "total_active_reports": len(report_dicts),
        "total_clusters": len(clusters),
        "duplicate_clusters_count": len(duplicate_clusters),
        "duplicate_clusters": duplicate_clusters,
        "all_clusters": clusters,
        "policy": "Suspected duplicate candidates are grouped for officer review; no reports are automatically deleted.",
    }


@router.get("/ml/benchmark")
async def get_ml_benchmark_metrics():
    """
    Returns scikit-learn model evaluation metrics comparing Random Forest and Gradient Boosting
    against the rule-based risk engine on a stratified 80/20 test split.
    Tracks Accuracy, Precision, Recall, F1-Score, Confusion Matrix, and Feature Importances.
    """
    return ml_baseline.get_evaluation_metrics()
