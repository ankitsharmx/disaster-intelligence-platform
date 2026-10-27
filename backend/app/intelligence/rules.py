from typing import Dict, Any, List


class RiskRuleEngine:
    """Evaluates multi-sensor thresholds and generates risk assessments."""

    @staticmethod
    def evaluate_rainfall(rainfall_1h_mm: float) -> Dict[str, Any]:
        if rainfall_1h_mm >= 80.0:
            return {"level": "critical", "color": "red", "action": "Issue Immediate Red Alert"}
        elif rainfall_1h_mm >= 50.0:
            return {"level": "high", "color": "orange", "action": "Issue Orange Warning / Prepare Shelters"}
        elif rainfall_1h_mm >= 25.0:
            return {"level": "medium", "color": "yellow", "action": "Issue Advisory / Clear Drains"}
        return {"level": "low", "color": "green", "action": "Routine Monitoring"}

    @staticmethod
    def evaluate_river_level(current_m: float, danger_m: float) -> Dict[str, Any]:
        diff = current_m - danger_m
        if diff >= 0.5:
            return {"level": "critical", "overflow_m": diff, "message": "Severe embankment overtopping risk"}
        elif diff >= 0.0:
            return {"level": "high", "overflow_m": diff, "message": "River flowing above danger mark"}
        elif diff >= -0.5:
            return {"level": "medium", "overflow_m": diff, "message": "Approaching danger mark"}
        return {"level": "low", "overflow_m": diff, "message": "Normal river stage"}

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
        return {"level": "low", "message": "Standard observation"}
