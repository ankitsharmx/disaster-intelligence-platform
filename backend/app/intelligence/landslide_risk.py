"""
Landslide Risk Engine (Deterministic / Rule-Based).
Evaluates terrain slope gradients, 72-hour antecedent precipitation index (API),
soil saturation percentage, and historical landslide hazard vulnerability (Geological Survey of India criteria).
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.intelligence.feature_extraction import FeatureExtractor


class LandslideRiskEngine:
    """
    Evaluates terrain stability and antecedent hydrometeorological triggers.
    All outputs explicitly carry 'isOfficialWarning: false' and indicative labeling.
    """

    METHOD_ID = "RULE_BASED_V1_TERRAIN_GSI"
    DISCLAIMER = "Indicative risk — not an official warning."

    # Documented antecedent rainfall trigger thresholds for Western Ghats / Konkan slopes
    # Ref: Geological Survey of India (GSI) Landslide Susceptibility Guidelines
    ANTECEDENT_72H_CRITICAL = 250.0  # >250 mm in 72h + steep slope = imminent slope instability
    ANTECEDENT_72H_HIGH = 150.0      # 150 - 250 mm: high pore-water pressure buildup
    ANTECEDENT_72H_MEDIUM = 80.0     # 80 - 150 mm: moderate saturation

    INTENSITY_24H_TRIGGER = 60.0     # >60 mm in 24h triggers active debris slide initiation

    CRITICAL_SLOPE_DEG = 30.0        # Slopes > 30 degrees have high gravitational shear stress
    MODERATE_SLOPE_DEG = 15.0

    @classmethod
    def calculate_risk(
        cls,
        observations: Dict[str, Any],
        district_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calculates structured indicative landslide risk."""
        feats = FeatureExtractor.extract_environmental_features(observations, district_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        r24h = feats["rainfall_24h_mm"]
        r72h = feats["rainfall_72h_mm"]
        avg_slope = feats["avg_slope_deg"]
        max_slope = feats["max_slope_deg"]
        soil_sat = feats["soil_saturation_pct"]
        hist_landslide_risk = feats["historical_landslide_risk"]

        # 1. Slope vulnerability factor
        slope_factor = "low_gradient"
        slope_score = 0
        if max_slope >= cls.CRITICAL_SLOPE_DEG:
            slope_factor = "steep_scarp_slopes"
            slope_score = 3
        elif max_slope >= cls.MODERATE_SLOPE_DEG:
            slope_factor = "moderate_slopes"
            slope_score = 2
        else:
            slope_factor = "gentle_plains"
            slope_score = 0

        # If area is virtually flat (avg_slope < 5 deg and max_slope < 12 deg e.g. Mumbai City),
        # landslide risk remains low regardless of rainfall.
        if max_slope < 15.0:
            return {
                "hazardType": "LANDSLIDE",
                "riskLevel": "LOW",
                "isOfficialWarning": False,
                "method": cls.METHOD_ID,
                "calculatedAt": now_iso,
                "disclaimer": cls.DISCLAIMER,
                "factors": {
                    "terrainSlope": "low_gradient_terrain",
                    "rainfallAccumulation": "not_applicable_flat_terrain",
                    "soilSaturation": f"{soil_sat}%",
                    "historicalLandslides": "unlikely",
                },
                "metrics": {
                    "rainfall_72h_mm": r72h,
                    "rainfall_24h_mm": r24h,
                    "avg_slope_deg": avg_slope,
                    "max_slope_deg": max_slope,
                    "soil_saturation_pct": soil_sat,
                },
                "recommendedAction": "Topography is non-susceptible to mass movement landslides.",
                "confidence": "HIGH",
            }

        # 2. Rainfall antecedent trigger score
        rain_factor = "dry/nominal"
        rain_score = 0
        if r72h >= cls.ANTECEDENT_72H_CRITICAL or (r72h >= cls.ANTECEDENT_72H_HIGH and r24h >= cls.INTENSITY_24H_TRIGGER):
            rain_factor = "extreme_pore_pressure"
            rain_score = 4
        elif r72h >= cls.ANTECEDENT_72H_HIGH:
            rain_factor = "high_saturation"
            rain_score = 3
        elif r72h >= cls.ANTECEDENT_72H_MEDIUM:
            rain_factor = "moderate_saturation"
            rain_score = 2
        else:
            rain_factor = "low_saturation"
            rain_score = 0

        # 3. Historical vulnerability factor
        hist_factor = "chronic_landslide_zone" if hist_landslide_risk >= 0.7 else ("occasional_slips" if hist_landslide_risk >= 0.4 else "rare")

        # 4. Composite Landslide Risk Calculation
        composite_score = 0
        if rain_score >= 3 and slope_score >= 3:
            composite_score = 4  # Critical
        elif rain_score >= 2 and slope_score >= 2 and hist_landslide_risk >= 0.5:
            composite_score = 3  # High
        elif rain_score >= 2 or (rain_score >= 1 and slope_score >= 3):
            composite_score = 2  # Medium
        elif rain_score >= 1:
            composite_score = 1  # Low
        else:
            composite_score = 0  # Low

        level_map = {
            4: "CRITICAL",
            3: "HIGH",
            2: "MEDIUM",
            1: "LOW",
            0: "LOW",
        }
        risk_level = level_map[composite_score]

        action_map = {
            "CRITICAL": "Pre-emptive evacuation of settlements on hillside toes and ghat cuttings. Suspend ghat vehicular traffic.",
            "HIGH": "Issue hillside advisory. Inspect chronic tension cracks and clear landslide drainage culverts.",
            "MEDIUM": "Advisory for ghat travelers and hill-slope residents. Monitor continuous rainfall gauges.",
            "LOW": "Routine terrain monitoring. No immediate slope movement alerts.",
        }

        return {
            "hazardType": "LANDSLIDE",
            "riskLevel": risk_level,
            "isOfficialWarning": False,
            "method": cls.METHOD_ID,
            "calculatedAt": now_iso,
            "disclaimer": cls.DISCLAIMER,
            "factors": {
                "terrainSlope": slope_factor,
                "rainfallAccumulation": rain_factor,
                "soilSaturation": f"{soil_sat}%",
                "historicalLandslides": hist_factor,
            },
            "metrics": {
                "rainfall_72h_mm": r72h,
                "rainfall_24h_mm": r24h,
                "avg_slope_deg": avg_slope,
                "max_slope_deg": max_slope,
                "soil_saturation_pct": soil_sat,
            },
            "recommendedAction": action_map[risk_level],
            "confidence": "HIGH" if feats["has_rainfall_data"] else "MEDIUM",
        }
