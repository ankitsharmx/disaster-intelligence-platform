"""
Feature extraction module for disaster intelligence and risk estimation.
Normalizes environmental sensor records, terrain attributes, and incident report metadata
into structured feature dictionaries and numeric vectors for rules-based and ML models.
"""
from typing import Dict, Any, List, Optional, Tuple
import numpy as np


class FeatureExtractor:
    """Extracts standardized feature vectors from environmental and incident inputs."""

    # Documented terrain slope and hazard profiles for supported Maharashtra districts
    DISTRICT_TERRAIN_PROFILES: Dict[int, Dict[str, Any]] = {
        1: {"name": "Mumbai City", "avg_slope_deg": 3.5, "max_slope_deg": 12.0, "soil_type": "alluvial/coastal", "historical_flood_risk": 0.85, "historical_landslide_risk": 0.10},
        2: {"name": "Mumbai Suburban", "avg_slope_deg": 6.2, "max_slope_deg": 28.0, "soil_type": "clayey/hills", "historical_flood_risk": 0.90, "historical_landslide_risk": 0.45},
        3: {"name": "Thane", "avg_slope_deg": 11.4, "max_slope_deg": 38.0, "soil_type": "laterite/rocky", "historical_flood_risk": 0.70, "historical_landslide_risk": 0.60},
        4: {"name": "Pune", "avg_slope_deg": 9.8, "max_slope_deg": 32.0, "soil_type": "black_cotton/basalt", "historical_flood_risk": 0.65, "historical_landslide_risk": 0.50},
        5: {"name": "Raigad", "avg_slope_deg": 18.5, "max_slope_deg": 52.0, "soil_type": "laterite/mountainous", "historical_flood_risk": 0.75, "historical_landslide_risk": 0.85},
        6: {"name": "Ratnagiri", "avg_slope_deg": 16.2, "max_slope_deg": 48.0, "soil_type": "coastal_laterite", "historical_flood_risk": 0.70, "historical_landslide_risk": 0.80},
    }

    DEFAULT_TERRAIN = {
        "name": "General District",
        "avg_slope_deg": 8.0,
        "max_slope_deg": 25.0,
        "soil_type": "mixed",
        "historical_flood_risk": 0.50,
        "historical_landslide_risk": 0.30,
    }

    @classmethod
    def get_district_profile(cls, district_id: Optional[int]) -> Dict[str, Any]:
        """Returns documented topographic and hazard vulnerability profile."""
        if district_id and district_id in cls.DISTRICT_TERRAIN_PROFILES:
            return cls.DISTRICT_TERRAIN_PROFILES[district_id]
        return cls.DEFAULT_TERRAIN

    @classmethod
    def extract_environmental_features(
        cls,
        observations: Dict[str, Any],
        district_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Extracts structured environmental indicators from multi-hazard observations:
        - Rainfall rates (1h, 24h, 72h mm)
        - River hydraulic stage vs danger threshold (meters)
        - Topographic slope parameters
        - Historical hazard vulnerability
        """
        terrain = cls.get_district_profile(district_id)

        # 1. Rainfall extraction
        rainfall_obs = observations.get("rainfall", {})
        rain_vals = rainfall_obs.get("values", {}) if isinstance(rainfall_obs, dict) else {}
        if not rain_vals and "rainfall_1h_mm" in observations:
            rain_vals = observations

        r1h = float(rain_vals.get("rainfall_1h_mm", 0.0) or 0.0)
        r24h = float(rain_vals.get("rainfall_24h_mm", r1h * 4.5) or 0.0)
        r72h = float(rain_vals.get("rainfall_72h_mm", r24h * 1.8) or 0.0)

        # 2. River level extraction
        flood_obs = observations.get("flood", {})
        flood_vals = flood_obs.get("values", {}) if isinstance(flood_obs, dict) else {}
        if not flood_vals and "water_level_meters" in observations:
            flood_vals = observations

        cur_water_m = float(flood_vals.get("water_level_meters", 0.0) or 0.0)
        danger_m = float(flood_vals.get("danger_mark_meters", 0.0) or 0.0)
        warning_m = float(flood_vals.get("warning_mark_meters", danger_m * 0.85 if danger_m else 0.0) or 0.0)
        river_overflow_delta = (cur_water_m - danger_m) if danger_m > 0 else 0.0

        # 3. Soil moisture & slope indicators
        soil_saturation_pct = min(100.0, max(15.0, (r72h / 150.0) * 100.0))

        return {
            "rainfall_1h_mm": round(r1h, 2),
            "rainfall_24h_mm": round(r24h, 2),
            "rainfall_72h_mm": round(r72h, 2),
            "water_level_meters": round(cur_water_m, 2),
            "danger_mark_meters": round(danger_m, 2),
            "warning_mark_meters": round(warning_m, 2),
            "river_overflow_delta": round(river_overflow_delta, 2),
            "river_has_gauge": danger_m > 0,
            "avg_slope_deg": terrain["avg_slope_deg"],
            "max_slope_deg": terrain["max_slope_deg"],
            "soil_saturation_pct": round(soil_saturation_pct, 1),
            "historical_flood_risk": terrain["historical_flood_risk"],
            "historical_landslide_risk": terrain["historical_landslide_risk"],
            "has_rainfall_data": "rainfall" in observations or r1h > 0,
            "has_river_data": danger_m > 0,
        }

    @classmethod
    def to_ml_feature_vector(cls, features: Dict[str, Any]) -> np.ndarray:
        """Converts extracted feature dict to fixed-size numpy array for ML model."""
        return np.array([
            features.get("rainfall_1h_mm", 0.0),
            features.get("rainfall_24h_mm", 0.0),
            features.get("rainfall_72h_mm", 0.0),
            features.get("water_level_meters", 0.0),
            features.get("river_overflow_delta", 0.0),
            1.0 if features.get("river_has_gauge") else 0.0,
            features.get("avg_slope_deg", 8.0),
            features.get("max_slope_deg", 25.0),
            features.get("soil_saturation_pct", 30.0),
            features.get("historical_flood_risk", 0.5),
            features.get("historical_landslide_risk", 0.3),
        ], dtype=float)

    FEATURE_NAMES: List[str] = [
        "rainfall_1h_mm",
        "rainfall_24h_mm",
        "rainfall_72h_mm",
        "water_level_meters",
        "river_overflow_delta",
        "river_has_gauge",
        "avg_slope_deg",
        "max_slope_deg",
        "soil_saturation_pct",
        "historical_flood_risk",
        "historical_landslide_risk",
    ]
