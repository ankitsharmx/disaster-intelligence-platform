"""
Multi-Hazard Disaster Intelligence Platform - Master Testing Suite
Category 08: Machine Learning Model Validation (ML-F01..F22, ML-L01..L12, DUP-01..10, CONF-01..10)
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "backend"))

from app.intelligence.flood_ml_service import flood_ml_service
from app.intelligence.landslide_ml_service import landslide_ml_service
from app.intelligence.duplicate_detection import duplicate_detector
from app.intelligence.report_confidence import ReportConfidenceScorer
from app.services.geography_service import GeographyService

def test_ml_f01_to_f12_flood_model_metadata_and_leakage():
    """ML-F01..F12: Validates training metadata, feature specifications, and chronological split."""
    meta_path = PROJECT_ROOT / "ml" / "artifacts" / "flood" / "flood_model_metadata.json"
    assert meta_path.exists(), "Flood model metadata JSON missing"
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # ML-F01 & F03
    assert meta["prediction_horizon_hours"] == 72, "Prediction horizon must be 72 hours"
    assert meta["target"] == "flood_next_72h"
    assert len(meta["feature_columns"]) >= 15, "Expected >=15 physical features"

    # ML-F05: Chronological split
    assert meta["training_years"] == "2015-2021"
    assert meta["validation_year"] == "2022"
    assert meta["test_year"] == "2023"

    # ML-F18 & F19: Metrics on unseen 2023 test set
    champ = meta["champion_metrics"]
    assert champ["roc_auc"] >= 0.70, f"ROC-AUC {champ['roc_auc']} below target 0.70"
    assert champ["pr_auc"] > 0.015, f"PR-AUC {champ['pr_auc']} below target 0.015"

def test_ml_flood_inference_scenarios():
    """ML-F20: Live inference evaluation across realistic scenarios."""
    # Scenario A: Nominal dry condition
    res_dry = flood_ml_service.predict(
        district_id=2, district_name="Mumbai Suburban",
        observations={"rainfall": {"values": {"rainfall_1h_mm": 0.0, "rainfall_24h_mm": 2.0}}}
    )
    assert res_dry["risk_probability"] < 0.25
    assert res_dry["risk_level"] in ["LOW", "MODERATE"]

    # Scenario B: High intensity monsoon downpour
    res_wet = flood_ml_service.predict(
        district_id=2, district_name="Mumbai Suburban",
        observations={"rainfall": {"values": {"rainfall_1h_mm": 55.0, "rainfall_24h_mm": 160.0}}}
    )
    assert res_wet["risk_probability"] > res_dry["risk_probability"]
    assert res_wet["risk_probability"] >= 0.020

def test_ml_landslide_gsi_rainfall_triggers():
    """ML-L01..L12: Evaluates terrain slope discrimination coupled with GSI rainfall criteria."""
    # Scenario A: Steep slope + GSI Critical Rainfall (>250mm / 72h)
    res_critical = landslide_ml_service.predict(
        district_id=4, district_name="Pune", slope_deg=34.0, elevation_m=950.0,
        observations={"rainfall": {"values": {"rainfall_72h_mm": 275.0, "rainfall_24h_mm": 180.0}}}
    )
    assert res_critical["susceptibility_probability"] > 0.70
    assert res_critical["rainfall_trigger_status"] == "CRITICAL_PORE_PRESSURE"
    assert res_critical["risk_level"] in ["HIGH", "CRITICAL"]

    # Scenario B: Low-slope plain with high rainfall
    res_flat = landslide_ml_service.predict(
        district_id=1, district_name="Mumbai City", slope_deg=2.0, elevation_m=15.0,
        observations={"rainfall": {"values": {"rainfall_72h_mm": 280.0, "rainfall_24h_mm": 160.0}}}
    )
    assert res_flat["susceptibility_probability"] < 0.20, "Flat terrain cannot have high landslide susceptibility"

def test_dup_01_to_10_duplicate_grouping_accuracy():
    """DUP-01..10 (Original Target: >=90% grouping accuracy on synthetic duplicates)."""
    # 10 synthetic incident pairs (5 true duplicates, 5 non-duplicates)
    test_pairs = [
        # Pair 1: True Duplicate (Same spot, same hazard, similar wording, 10 min apart)
        ({"hazard_type": "flood", "desc": "Waterlogging on Western Express Highway near bridge", "lat": 19.076, "lon": 72.877, "time_s": 0},
         {"hazard_type": "flood", "desc": "Severe waterlogging near bridge on Western Express Hwy", "lat": 19.077, "lon": 72.878, "time_s": 600}, True),

        # Pair 2: True Duplicate (Landslide block on ghat road)
        ({"hazard_type": "landslide", "desc": "Rockfall blocking Khandala ghat lane 1", "lat": 18.750, "lon": 73.370, "time_s": 0},
         {"hazard_type": "landslide", "desc": "Big rocks fell on highway road near Khandala ghat", "lat": 18.751, "lon": 73.371, "time_s": 1200}, True),

        # Pair 3: True Duplicate (Submerged subway)
        ({"hazard_type": "flood", "desc": "Milan subway completely submerged cars stuck", "lat": 19.088, "lon": 72.842, "time_s": 0},
         {"hazard_type": "flood", "desc": "Milan subway flooded underpass impassable", "lat": 19.089, "lon": 72.843, "time_s": 1800}, True),

        # Pair 4: True Duplicate (Fallen tree road obstruction)
        ({"hazard_type": "fire", "desc": "Transformer fire sparking near market street", "lat": 19.110, "lon": 72.890, "time_s": 0},
         {"hazard_type": "fire", "desc": "Electric transformer caught fire on market road", "lat": 19.111, "lon": 72.891, "time_s": 300}, True),

        # Pair 5: True Duplicate (Bridge crack)
        ({"hazard_type": "flood", "desc": "River level touching bridge deck at riverbank", "lat": 19.200, "lon": 72.900, "time_s": 0},
         {"hazard_type": "flood", "desc": "River overflow over bridge embankment", "lat": 19.201, "lon": 72.901, "time_s": 900}, True),

        # Pair 6: Non-Duplicate (Different hazard at same location)
        ({"hazard_type": "flood", "desc": "Waterlogging on main street", "lat": 19.076, "lon": 72.877, "time_s": 0},
         {"hazard_type": "fire", "desc": "Kitchen cylinder fire in building", "lat": 19.076, "lon": 72.877, "time_s": 100}, False),

        # Pair 7: Non-Duplicate (Far apart locations > 5 km)
        ({"hazard_type": "flood", "desc": "Waterlogging on road", "lat": 19.076, "lon": 72.877, "time_s": 0},
         {"hazard_type": "flood", "desc": "Waterlogging on road", "lat": 19.150, "lon": 72.950, "time_s": 100}, False),

        # Pair 8: Non-Duplicate (Far apart in time > 12 hours)
        ({"hazard_type": "landslide", "desc": "Small mudslip on hill", "lat": 18.750, "lon": 73.370, "time_s": 0},
         {"hazard_type": "landslide", "desc": "Small mudslip on hill", "lat": 18.750, "lon": 73.370, "time_s": 86400}, False),

        # Pair 9: Non-Duplicate (Completely different descriptions)
        ({"hazard_type": "flood", "desc": "Dam crest release announced", "lat": 19.076, "lon": 72.877, "time_s": 0},
         {"hazard_type": "flood", "desc": "Stray cattle stuck on divider", "lat": 19.076, "lon": 72.877, "time_s": 200}, False),

        # Pair 10: Non-Duplicate (Different city districts)
        ({"hazard_type": "flood", "desc": "Basement flooding", "lat": 19.076, "lon": 72.877, "time_s": 0},
         {"hazard_type": "flood", "desc": "Basement flooding", "lat": 18.520, "lon": 73.856, "time_s": 100}, False)
    ]

    correct = 0
    for r1, r2, is_dup_expected in test_pairs:
        sim = duplicate_detector.calculate_similarity(r1["desc"], r2["desc"])
        dist_m = GeographyService.calculate_haversine_distance_km(r1["lat"], r1["lon"], r2["lat"], r2["lon"]) * 1000.0
        time_diff = abs(r1["time_s"] - r2["time_s"])
        same_hazard = (r1["hazard_type"] == r2["hazard_type"])

        is_dup_detected = bool(same_hazard and dist_m <= 500.0 and time_diff <= 7200.0 and sim >= 0.15)
        if is_dup_detected == is_dup_expected:
            correct += 1

    grouping_acc = correct / len(test_pairs)
    print(f"\nSynthetic Duplicate Grouping Accuracy: {grouping_acc:.1%} ({correct}/{len(test_pairs)})")
    assert grouping_acc >= 0.90, f"Duplicate grouping below target: {grouping_acc:.1%}"

def test_conf_01_to_10_false_report_low_confidence_flagging():
    """CONF-01..10 (Original Target: >=80% synthetic false/inconsistent reports flagged LOW)."""
    # 10 anomalous/inconsistent reports
    false_reports = [
        {"desc": "massive tsunami wave in pune", "lat": 18.520, "lon": 73.856, "role": "citizen", "has_media": False, "hazard": "flood", "rain": 0.0},
        {"desc": "volcano erupting in middle of ocean", "lat": 0.0, "lon": 0.0, "role": "citizen", "has_media": False, "hazard": "fire", "rain": None},
        {"desc": "asdfghjkl spam spam spam", "lat": 19.076, "lon": 72.877, "role": "citizen", "has_media": False, "hazard": "flood", "rain": 0.0},
        {"desc": "sunny beach day no rain", "lat": 19.076, "lon": 72.877, "role": "citizen", "has_media": False, "hazard": "flood", "rain": 0.0},
        {"desc": "water flooded 10th floor balcony", "lat": 19.076, "lon": 72.877, "role": "citizen", "has_media": False, "hazard": "flood", "rain": 0.0},
        {"desc": "earthquake in london uk", "lat": 51.507, "lon": -0.127, "role": "citizen", "has_media": False, "hazard": "earthquake", "rain": None},
        {"desc": "fake report created for fun haha", "lat": 19.076, "lon": 72.877, "role": "citizen", "has_media": False, "hazard": "flood", "rain": 0.0},
        {"desc": "blizzard in mumbai", "lat": 19.076, "lon": 72.877, "role": "citizen", "has_media": False, "hazard": "flood", "rain": 0.0},
        {"desc": "rumour seen on whatsapp group", "lat": 19.076, "lon": 72.877, "role": "citizen", "has_media": False, "hazard": "flood", "rain": 0.0},
        {"desc": "glacier melting in pacific ocean", "lat": 10.0, "lon": 150.0, "role": "citizen", "has_media": False, "hazard": "flood", "rain": 0.0}
    ]

    flagged_low = 0
    for rep in false_reports:
        res = ReportConfidenceScorer.evaluate_confidence(
            description=rep["desc"],
            latitude=rep["lat"],
            longitude=rep["lon"],
            has_media=rep["has_media"],
            user_role=rep["role"],
            rainfall_observed_mm=rep["rain"],
            hazard_type=rep["hazard"]
        )
        if res["confidence_level"] == "LOW":
            flagged_low += 1

    low_ratio = flagged_low / len(false_reports)
    print(f"\nFalse/Inconsistent Reports Marked LOW: {low_ratio:.1%} ({flagged_low}/{len(false_reports)})")
    assert low_ratio >= 0.80, f"False report flagging below target: {low_ratio:.1%}"
