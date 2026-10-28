"""
Flood Risk Engine (Deterministic / Rule-Based).
Computes structured indicative flood risks from meteorological rainfall observations (IMD standards),
hydrological river stage sensors (CWC standards), and district historical vulnerability.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.intelligence.feature_extraction import FeatureExtractor


class FloodRiskEngine:
    """
    Evaluates multi-sensor inputs to calculate an indicative flood risk assessment.
    All outputs explicitly carry 'isOfficialWarning: false' and indicative labeling.
    """

    METHOD_ID = "RULE_BASED_V1_IMD_CWC"
    DISCLAIMER = "Indicative risk — not an official warning."

    # IMD (India Meteorological Department) Rainfall Intensity Thresholds (mm/hr & mm/24hr)
    # Ref: IMD Standard Weather Glossary & Heavy Rainfall Criteria
    IMD_1H_CRITICAL = 70.0   # >70 mm/hr: Cloudburst / extreme localized inundation
    IMD_1H_HIGH = 45.0       # 45-70 mm/hr: Very heavy downpour
    IMD_1H_MEDIUM = 20.0     # 20-45 mm/hr: Moderate to heavy rain (urban waterlogging)
    IMD_1H_LOW = 5.0         # 5-20 mm/hr: Light to moderate

    IMD_24H_EXTREME = 204.4  # Extremely Heavy (>204.4 mm)
    IMD_24H_VERY_HEAVY = 115.5 # Very Heavy (115.6 - 204.4 mm)
    IMD_24H_HEAVY = 64.5     # Heavy (64.5 - 115.5 mm)

    @classmethod
    def calculate_risk(
        cls,
        observations: Dict[str, Any],
        district_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calculates structured indicative flood risk for a district or observation set.
        """
        feats = FeatureExtractor.extract_environmental_features(observations, district_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        r1h = feats["rainfall_1h_mm"]
        r24h = feats["rainfall_24h_mm"]
        overflow = feats["river_overflow_delta"]
        has_gauge = feats["river_has_gauge"]
        cur_water = feats["water_level_meters"]
        danger_mark = feats["danger_mark_meters"]
        warning_mark = feats["warning_mark_meters"]
        hist_risk = feats["historical_flood_risk"]

        # 1. Rainfall factor assessment
        rainfall_factor = "normal"
        rainfall_score = 0
        if r1h >= cls.IMD_1H_CRITICAL or r24h >= cls.IMD_24H_EXTREME:
            rainfall_factor = "extreme"
            rainfall_score = 4
        elif r1h >= cls.IMD_1H_HIGH or r24h >= cls.IMD_24H_VERY_HEAVY:
            rainfall_factor = "severe"
            rainfall_score = 3
        elif r1h >= cls.IMD_1H_MEDIUM or r24h >= cls.IMD_24H_HEAVY:
            rainfall_factor = "elevated"
            rainfall_score = 2
        elif r1h >= cls.IMD_1H_LOW:
            rainfall_factor = "moderate"
            rainfall_score = 1

        # 2. River level factor assessment
        river_factor = "unmonitored" if not has_gauge else "normal"
        river_score = 0
        if has_gauge:
            if overflow >= 0.5:
                river_factor = "critical_overtopping"
                river_score = 4
            elif overflow >= 0.0:
                river_factor = "above_danger_mark"
                river_score = 3
            elif cur_water >= warning_mark:
                river_factor = "approaching_danger"
                river_score = 2
            else:
                river_factor = "within_banks"
                river_score = 0

        # 3. Historical vulnerability factor
        hist_factor = "high_vulnerability" if hist_risk >= 0.8 else ("moderate_vulnerability" if hist_risk >= 0.5 else "low_vulnerability")

        # 4. Composite Risk Level Determination
        # Max of direct triggers, with historical weighting
        max_trigger_score = max(rainfall_score, river_score)
        
        # If rainfall is elevated and historical vulnerability is high, nudge risk
        if rainfall_score >= 2 and hist_risk >= 0.8 and max_trigger_score < 3:
            composite_score = 3
        else:
            composite_score = max_trigger_score

        level_map = {
            4: "CRITICAL",
            3: "HIGH",
            2: "MEDIUM",
            1: "LOW",
            0: "LOW",
        }
        risk_level = level_map[composite_score]

        action_map = {
            "CRITICAL": "Immediate evacuation of low-lying floodplains. Deploy NDRF/SDRF emergency boats.",
            "HIGH": "Activate emergency shelters. Close flooded subways and clear arterial stormwater channels.",
            "MEDIUM": "Issue local waterlogging advisory. Pre-position dewatering pumps at chronic inundation spots.",
            "LOW": "Routine hydrological surveillance. Monitor upstream dam discharge bulletins.",
        }

        return {
            "hazardType": "FLOOD",
            "riskLevel": risk_level,
            "isOfficialWarning": False,
            "method": cls.METHOD_ID,
            "calculatedAt": now_iso,
            "disclaimer": cls.DISCLAIMER,
            "factors": {
                "rainfall": rainfall_factor,
                "riverLevel": river_factor,
                "historicalFloods": hist_factor,
            },
            "metrics": {
                "rainfall_1h_mm": r1h,
                "rainfall_24h_mm": r24h,
                "water_level_meters": cur_water,
                "danger_mark_meters": danger_mark,
                "overflow_meters": round(overflow, 2) if has_gauge else None,
            },
            "recommendedAction": action_map[risk_level],
            "confidence": "HIGH" if (feats["has_rainfall_data"] and has_gauge) else ("MEDIUM" if feats["has_rainfall_data"] else "LOW"),
        }
