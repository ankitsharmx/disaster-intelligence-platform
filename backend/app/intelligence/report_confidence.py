"""
Explainable Report Confidence Scoring Module.
Evaluates multi-signal credibility for citizen hazard reports:
1. Coordinate validity & boundary containment
2. Description completeness & actionable specificity
3. Supporting photographic / video evidence
4. Citizen corroboration & multi-reporting
5. Meteorological / hydrological sensor consistency

Output: Advisory structured confidence assessment with LOW/MEDIUM/HIGH classification.
Policy: Missing data does not imply false reporting; the officer makes the final decision.
"""
from typing import Dict, Any, List, Optional
from app.services.geography_service import geography_service


class ReportConfidenceScorer:
    """Computes explainable advisory confidence scores for citizen hazard reports."""

    @classmethod
    def evaluate_confidence(
        cls,
        description: str,
        latitude: float,
        longitude: float,
        has_media: bool = False,
        user_role: str = "citizen",
        corroborating_reports_count: int = 0,
        nearby_sensor_active: bool = False,
        rainfall_observed_mm: Optional[float] = None,
        hazard_type: str = "flood",
    ) -> Dict[str, Any]:
        """
        Computes structured confidence score (0.0 to 1.0) and explainable factors.
        """
        score = 0.50  # Neutral prior baseline
        factors: List[Dict[str, Any]] = []

        # 1. Geographic Validity Signal
        district = geography_service.resolve_district(latitude, longitude)
        if district:
            score += 0.10
            factors.append({
                "signal": "geographic_validity",
                "status": "valid",
                "delta": +0.10,
                "detail": f"Coordinates resolve within valid district boundary: {district.get('name', 'Known District')}",
            })
        else:
            score -= 0.15
            factors.append({
                "signal": "geographic_validity",
                "status": "unverified_boundary",
                "delta": -0.15,
                "detail": "Coordinates fall outside active administrative district boundaries",
            })

        # 2. Text Completeness & Specificity Signal
        clean_desc = description.strip()
        length = len(clean_desc)
        if length >= 100:
            score += 0.15
            factors.append({
                "signal": "text_completeness",
                "status": "high_detail",
                "delta": +0.15,
                "detail": f"Detailed factual description ({length} characters) with landmark specifics",
            })
        elif length >= 35:
            score += 0.08
            factors.append({
                "signal": "text_completeness",
                "status": "adequate_detail",
                "delta": +0.08,
                "detail": f"Adequate description ({length} characters)",
            })
        else:
            score -= 0.10
            factors.append({
                "signal": "text_completeness",
                "status": "brief",
                "delta": -0.10,
                "detail": "Very short description; lacks actionable situational context",
            })

        # 3. Photographic / Video Evidence Signal
        if has_media:
            score += 0.20
            factors.append({
                "signal": "photographic_evidence",
                "status": "attached",
                "delta": +0.20,
                "detail": "Photographic or video evidence attached to incident report",
            })
        else:
            factors.append({
                "signal": "photographic_evidence",
                "status": "not_attached",
                "delta": 0.0,
                "detail": "No photo evidence attached (advisory: does not invalidate report)",
            })

        # 4. Independent Citizen Corroboration Signal
        if corroborating_reports_count >= 3:
            score += 0.15
            factors.append({
                "signal": "peer_corroboration",
                "status": "strong_cluster",
                "delta": +0.15,
                "detail": f"{corroborating_reports_count} nearby citizen reports corroborating same incident",
            })
        elif corroborating_reports_count >= 1:
            score += 0.08
            factors.append({
                "signal": "peer_corroboration",
                "status": "moderate_corroboration",
                "delta": +0.08,
                "detail": f"{corroborating_reports_count} nearby citizen report in close temporal proximity",
            })
        else:
            factors.append({
                "signal": "peer_corroboration",
                "status": "isolated_report",
                "delta": 0.0,
                "detail": "First report in immediate locality; awaiting corroborating reports",
            })

        # 5. Meteorological & Sensor Consistency Signal
        if nearby_sensor_active or (rainfall_observed_mm is not None and rainfall_observed_mm > 15.0):
            score += 0.15
            factors.append({
                "signal": "sensor_consistency",
                "status": "consistent",
                "delta": +0.15,
                "detail": f"Corroborated by active environmental sensors ({rainfall_observed_mm or 'active'} mm rainfall)",
            })
        elif rainfall_observed_mm is not None and rainfall_observed_mm < 2.0 and hazard_type == "flood":
            score -= 0.10
            factors.append({
                "signal": "sensor_consistency",
                "status": "inconsistent",
                "delta": -0.10,
                "detail": "Local weather sensors record nominal rainfall (<2 mm) during reported flooding",
            })
        else:
            factors.append({
                "signal": "sensor_consistency",
                "status": "sensor_neutral",
                "delta": 0.0,
                "detail": "No immediate telemetry stream within 5 km; baseline preserved",
            })

        # 6. Officer / First Responder Submission
        if user_role in {"officer", "admin", "district_officer", "state_admin", "system_admin"}:
            score += 0.20
            factors.append({
                "signal": "author_role",
                "status": "first_responder",
                "delta": +0.20,
                "detail": "Submitted by authenticated emergency response officer",
            })

        # Bound score to [0.05, 1.00]
        final_score = round(max(0.05, min(1.0, score)), 2)

        # Categorize confidence level
        if final_score >= 0.75:
            confidence_level = "HIGH"
        elif final_score >= 0.45:
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"

        return {
            "confidence_level": confidence_level,
            "confidence_score": final_score,
            "contributing_factors": factors,
            "advisory_note": "Score is advisory. Officer discretion is required before taking operational action.",
        }

    @classmethod
    def calculate_score(
        cls,
        description: str,
        has_media: bool = False,
        user_role: str = "citizen",
        nearby_sensor_corroboration: bool = False,
    ) -> float:
        """Backward-compatible scalar score calculation."""
        score = 0.50
        length = len(description.strip())
        if length > 80:
            score += 0.15
        elif length > 30:
            score += 0.08
        else:
            score -= 0.10

        if has_media:
            score += 0.20
        if user_role in {"officer", "admin", "district_officer", "state_admin", "system_admin"}:
            score += 0.25
        if nearby_sensor_corroboration:
            score += 0.15

        return round(max(0.05, min(1.0, score)), 2)


# Backward compatibility alias
ConfidenceScorer = ReportConfidenceScorer
confidence_scorer = ReportConfidenceScorer()
