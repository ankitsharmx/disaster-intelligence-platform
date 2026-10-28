from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.geography import District, State
from app.models.hazard import HazardObservation, DataSourceRun
from app.models.alert import Alert, AlertArea
from app.models.awareness import AwarenessContent
from app.intelligence.rules import RiskRuleEngine
from app.intelligence.flood_risk import FloodRiskEngine
from app.intelligence.landslide_risk import LandslideRiskEngine
from app.core.exceptions import EntityNotFoundException


class OverviewService:
    """
    Synthesizes multi-source situational awareness for a given administrative district:
    - Latest valid hazard observations (with source mode: demo vs live)
    - Active applicable alerts (with official vs prototype tags)
    - Automated risk estimates computed from observations
    - Contextual disaster safety guidance
    - Source health and update timestamps
    """

    @staticmethod
    async def get_district_overview(db: AsyncSession, district_id: int) -> Dict[str, Any]:
        # 1. Retrieve district
        dist_res = await db.execute(
            select(District).options(selectinload(District.state)).filter(District.id == district_id)
        )
        district = dist_res.scalar_one_or_none()
        if not district:
            raise EntityNotFoundException("District", district_id)

        now = datetime.now(timezone.utc)

        # 2. Retrieve latest observations for this district or state-wide
        obs_query = (
            select(HazardObservation)
            .filter(
                (HazardObservation.district_id == district_id) | (HazardObservation.district_id.is_(None))
            )
            .order_by(HazardObservation.observed_time.desc())
            .limit(20)
        )
        obs_res = await db.execute(obs_query)
        all_obs = obs_res.scalars().all()

        # Group latest observation by hazard type
        latest_observations: Dict[str, Any] = {}
        for obs in all_obs:
            if obs.hazard_type not in latest_observations:
                # Determine source mode
                run_res = await db.execute(
                    select(DataSourceRun).filter(DataSourceRun.source == obs.source).order_by(DataSourceRun.retrieval_time.desc())
                )
                last_run = run_res.scalars().first()
                source_mode = last_run.mode if last_run else ("live" if "live" in obs.source else "demo")

                latest_observations[obs.hazard_type] = {
                    "id": obs.id,
                    "hazard_type": obs.hazard_type,
                    "values": obs.values,
                    "observed_time": obs.observed_time.isoformat() if obs.observed_time else None,
                    "source": obs.source,
                    "source_mode": source_mode,
                    "station_location": {
                        "latitude": obs.latitude,
                        "longitude": obs.longitude,
                    } if obs.latitude is not None else None,
                }

        # 3. Retrieve applicable active alerts for this district
        alerts_query = (
            select(Alert)
            .join(AlertArea, Alert.id == AlertArea.alert_id)
            .filter(
                AlertArea.district_id == district_id,
                Alert.status == "active",
                Alert.valid_to >= now,
            )
            .order_by(desc(Alert.created_at))
        )
        alerts_res = await db.execute(alerts_query)
        alerts_list = alerts_res.scalars().all()

        formatted_alerts = []
        highest_severity = "low"
        severity_ranks = {"low": 1, "medium": 2, "high": 3, "critical": 4}

        for a in alerts_list:
            if severity_ranks.get(a.severity.lower(), 1) > severity_ranks.get(highest_severity, 1):
                highest_severity = a.severity.lower()

            formatted_alerts.append({
                "id": a.id,
                "type": a.type,
                "title": a.title,
                "description": a.description,
                "severity": a.severity,
                "issuer": a.issuer,
                "is_official": a.is_official,
                "origin": "official" if a.is_official else "prototype_exercise",
                "valid_from": a.valid_from.isoformat() if a.valid_from else None,
                "valid_to": a.valid_to.isoformat() if a.valid_to else None,
            })

        # 4. Compute risk estimates using RiskRuleEngine and structured engines
        risk_assessments: Dict[str, Any] = {}
        for htype, obs_info in latest_observations.items():
            rule_eval = RiskRuleEngine.evaluate_observation(htype, obs_info["values"])
            risk_assessments[htype] = rule_eval

        # Structured Indicative Risk Assessments (Phase 5)
        flood_eval = FloodRiskEngine.calculate_risk(latest_observations, district_id=district_id)
        landslide_eval = LandslideRiskEngine.calculate_risk(latest_observations, district_id=district_id)
        risk_assessments["structured_flood"] = flood_eval
        risk_assessments["structured_landslide"] = landslide_eval
        risk_assessments["indicative_disclaimer"] = "Indicative risk — not an official warning."

        # 5. Retrieve safety guidance tailored to active hazard
        primary_hazard = "flood"
        if "rainfall" in latest_observations or "flood" in latest_observations:
            primary_hazard = "flood"
        elif "earthquake" in latest_observations:
            primary_hazard = "earthquake"
        elif "fire" in latest_observations:
            primary_hazard = "fire"

        awareness_query = select(AwarenessContent).filter(
            AwarenessContent.hazard == primary_hazard,
            AwarenessContent.language == "en",
        )
        aw_res = await db.execute(awareness_query)
        guidance_records = aw_res.scalars().all()
        safety_guidance = [
            {
                "hazard": g.hazard,
                "stage": g.stage,
                "title": g.title,
                "instructions": g.instructions,
            }
            for g in guidance_records
        ]

        # 6. Data Source Runs Health
        runs_res = await db.execute(select(DataSourceRun).order_by(DataSourceRun.retrieval_time.desc()).limit(10))
        recent_runs = runs_res.scalars().all()
        sources_status = [
            {
                "source": r.source,
                "mode": r.mode,
                "status": r.status,
                "records_count": r.records_count,
                "retrieval_time": r.retrieval_time.isoformat() if r.retrieval_time else None,
                "error": r.error,
            }
            for r in recent_runs
        ]

        return {
            "district": {
                "id": district.id,
                "name": district.name,
                "code": district.code,
                "state_id": district.state_id,
                "state_name": district.state.name if district.state else None,
                "center": [district.center_lat, district.center_lon],
            },
            "overall_status": {
                "highest_alert_severity": highest_severity,
                "active_alerts_count": len(formatted_alerts),
                "last_updated": now.isoformat(),
            },
            "observations": latest_observations,
            "applicable_alerts": formatted_alerts,
            "risk_estimates": risk_assessments,
            "safety_guidance": safety_guidance,
            "data_sources_status": sources_status,
        }


overview_service = OverviewService()
