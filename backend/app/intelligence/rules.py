from typing import Dict, Any, List, Optional
from app.intelligence.flood_risk import FloodRiskEngine
from app.intelligence.landslide_risk import LandslideRiskEngine


class RiskRuleEngine:
    """Evaluates multi-sensor thresholds and generates structured indicative risk assessments."""

    @staticmethod
    def evaluate_rainfall(rainfall_1h_mm: float) -> Dict[str, Any]:
        if rainfall_1h_mm >= 80.0:
            return {
                "level": "critical",
                "color": "red",
                "action": "Issue Immediate Red Alert",
                "isOfficialWarning": False,
                "disclaimer": "Indicative risk — not an official warning.",
            }
        elif rainfall_1h_mm >= 50.0:
            return {
                "level": "high",
                "color": "orange",
                "action": "Issue Orange Warning / Prepare Shelters",
                "isOfficialWarning": False,
                "disclaimer": "Indicative risk — not an official warning.",
            }
        elif rainfall_1h_mm >= 25.0:
            return {
                "level": "medium",
                "color": "yellow",
                "action": "Issue Advisory / Clear Drains",
                "isOfficialWarning": False,
                "disclaimer": "Indicative risk — not an official warning.",
            }
        return {
            "level": "low",
            "color": "green",
            "action": "Routine Monitoring",
            "isOfficialWarning": False,
            "disclaimer": "Indicative risk — not an official warning.",
        }

    @staticmethod
    def evaluate_river_level(current_m: float, danger_m: float) -> Dict[str, Any]:
        diff = current_m - danger_m
        if diff >= 0.5:
            return {
                "level": "critical",
                "color": "red",
                "overflow_m": diff,
                "message": "Severe embankment overtopping risk",
                "isOfficialWarning": False,
                "disclaimer": "Indicative risk — not an official warning.",
            }
        elif diff >= 0.0:
            return {
                "level": "high",
                "color": "orange",
                "overflow_m": diff,
                "message": "River flowing above danger mark",
                "isOfficialWarning": False,
                "disclaimer": "Indicative risk — not an official warning.",
            }
        elif diff >= -0.5:
            return {
                "level": "medium",
                "color": "yellow",
                "overflow_m": diff,
                "message": "Approaching danger mark",
                "isOfficialWarning": False,
                "disclaimer": "Indicative risk — not an official warning.",
            }
        return {
            "level": "low",
            "color": "green",
            "overflow_m": diff,
            "message": "Normal river stage",
            "isOfficialWarning": False,
            "disclaimer": "Indicative risk — not an official warning.",
        }

    @classmethod
    def evaluate_observation(cls, hazard_type: str, values: Dict[str, Any]) -> Dict[str, Any]:
        if hazard_type == "rainfall":
            r1h = values.get("rainfall_1h_mm", 0.0)
            return cls.evaluate_rainfall(r1h)
        elif hazard_type == "flood":
            cur = values.get("water_level_meters", 0.0)
            danger = values.get("danger_mark_meters", 0.0)
            if danger > 0:
                return cls.evaluate_river_level(cur, danger)
        elif hazard_type == "landslide":
            landslide_eval = LandslideRiskEngine.calculate_risk(values)
            return {
                "level": landslide_eval["riskLevel"].lower(),
                "color": "red" if landslide_eval["riskLevel"] == "CRITICAL" else ("orange" if landslide_eval["riskLevel"] == "HIGH" else "yellow"),
                "action": landslide_eval["recommendedAction"],
                "factors": landslide_eval["factors"],
                "isOfficialWarning": False,
                "disclaimer": landslide_eval["disclaimer"],
            }
        return {
            "level": "low",
            "color": "green",
            "message": "Standard observation",
            "isOfficialWarning": False,
            "disclaimer": "Indicative risk — not an official warning.",
        }
