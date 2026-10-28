"""
Phase 5 Intelligence and Risk Engine Test Suite.
Verifies:
1. Feature extraction and district terrain profiles.
2. Deterministic flood risk rules (IMD & CWC criteria).
3. Deterministic landslide risk rules (GSI slope & antecedent rainfall criteria).
4. Indicative risk labeling ('isOfficialWarning: false' and mandatory disclaimer).
5. Spatio-temporal & TF-IDF duplicate report clustering.
6. Multi-signal explainable confidence scoring (LOW/MEDIUM/HIGH with itemized factors).
7. Machine learning baseline evaluation (scikit-learn Random Forest & Gradient Boosting, F1, precision, recall, confusion matrix, feature importances).
8. Dedicated FastAPI intelligence endpoints (/api/v1/intelligence).
"""
import pytest
from fastapi.testclient import TestClient

from app.intelligence.feature_extraction import FeatureExtractor
from app.intelligence.flood_risk import FloodRiskEngine
from app.intelligence.landslide_risk import LandslideRiskEngine
from app.intelligence.duplicate_detection import DuplicateDetector, duplicate_detector
from app.intelligence.report_confidence import ReportConfidenceScorer
from app.intelligence.ml_baseline import MLRiskBaseline, ml_baseline


def test_feature_extraction_and_district_terrain():
    """Verifies environmental normalization and documented district terrain profiles."""
    mumbai_profile = FeatureExtractor.get_district_profile(1)
    assert mumbai_profile["name"] == "Mumbai City"
    assert mumbai_profile["max_slope_deg"] < 15.0  # Coastal plains

    raigad_profile = FeatureExtractor.get_district_profile(5)
    assert raigad_profile["name"] == "Raigad"
    assert raigad_profile["max_slope_deg"] > 40.0  # Western Ghats scarps

    # Extraction with multi-hazard dictionary
    obs = {
        "rainfall": {"values": {"rainfall_1h_mm": 45.0, "rainfall_24h_mm": 120.0}},
        "flood": {"values": {"water_level_meters": 5.2, "danger_mark_meters": 4.5}},
    }
    feats = FeatureExtractor.extract_environmental_features(obs, district_id=2)
    assert feats["rainfall_1h_mm"] == 45.0
    assert feats["rainfall_24h_mm"] == 120.0
    assert feats["water_level_meters"] == 5.2
    assert feats["river_overflow_delta"] == 0.7  # 5.2 - 4.5
    assert feats["river_has_gauge"] is True
    assert feats["has_rainfall_data"] is True

    # Vector conversion
    vec = FeatureExtractor.to_ml_feature_vector(feats)
    assert len(vec) == len(FeatureExtractor.FEATURE_NAMES)
    assert vec[0] == 45.0


def test_flood_risk_engine_deterministic_rules():
    """Verifies IMD and CWC deterministic flood rules and indicative disclaimer."""
    # 1. Low rainfall, river within banks -> LOW
    obs_low = {
        "rainfall": {"values": {"rainfall_1h_mm": 2.0, "rainfall_24h_mm": 10.0}},
        "flood": {"values": {"water_level_meters": 1.5, "danger_mark_meters": 4.5}},
    }
    low_res = FloodRiskEngine.calculate_risk(obs_low, district_id=2)
    assert low_res["hazardType"] == "FLOOD"
    assert low_res["riskLevel"] == "LOW"
    assert low_res["isOfficialWarning"] is False
    assert "Indicative risk" in low_res["disclaimer"]
    assert low_res["factors"]["rainfall"] == "normal"
    assert low_res["factors"]["riverLevel"] == "within_banks"

    # 2. Elevated rainfall in Pune (district 4, moderate historical vulnerability) -> MEDIUM
    obs_med = {
        "rainfall": {"values": {"rainfall_1h_mm": 30.0, "rainfall_24h_mm": 70.0}},
        "flood": {"values": {"water_level_meters": 2.0, "danger_mark_meters": 4.5}},
    }
    med_res = FloodRiskEngine.calculate_risk(obs_med, district_id=4)
    assert med_res["riskLevel"] == "MEDIUM"
    assert med_res["factors"]["rainfall"] == "elevated"

    # 3. Cloudburst downpour (85 mm/hr, IMD Critical) -> CRITICAL
    obs_crit = {
        "rainfall": {"values": {"rainfall_1h_mm": 85.0, "rainfall_24h_mm": 220.0}},
        "flood": {"values": {"water_level_meters": 5.4, "danger_mark_meters": 4.5}},
    }
    crit_res = FloodRiskEngine.calculate_risk(obs_crit, district_id=2)
    assert crit_res["riskLevel"] == "CRITICAL"
    assert crit_res["factors"]["rainfall"] == "extreme"
    assert crit_res["factors"]["riverLevel"] == "critical_overtopping"
    assert "evacuation" in crit_res["recommendedAction"].lower()


def test_landslide_risk_engine_deterministic_rules():
    """Verifies GSI terrain slope and antecedent rainfall rules."""
    # 1. Flat coastal plain (Mumbai City, district 1) -> Low regardless of rain
    obs_rain = {
        "rainfall": {"values": {"rainfall_72h_mm": 280.0, "rainfall_24h_mm": 120.0}},
    }
    flat_res = LandslideRiskEngine.calculate_risk(obs_rain, district_id=1)
    assert flat_res["hazardType"] == "LANDSLIDE"
    assert flat_res["riskLevel"] == "LOW"
    assert flat_res["isOfficialWarning"] is False
    assert "flat" in flat_res["factors"]["rainfallAccumulation"].lower() or "not_applicable" in flat_res["factors"]["rainfallAccumulation"].lower()

    # 2. Mountainous terrain (Raigad, district 5) + Heavy Antecedent Rainfall -> CRITICAL
    ghat_res = LandslideRiskEngine.calculate_risk(obs_rain, district_id=5)
    assert ghat_res["riskLevel"] == "CRITICAL"
    assert ghat_res["isOfficialWarning"] is False
    assert ghat_res["factors"]["terrainSlope"] == "steep_scarp_slopes"
    assert ghat_res["factors"]["rainfallAccumulation"] == "extreme_pore_pressure"
    assert "evacuation" in ghat_res["recommendedAction"].lower()


def test_duplicate_detection_and_clustering():
    """Verifies spatio-temporal grouping and TF-IDF text similarity clustering."""
    detector = DuplicateDetector(max_distance_meters=400.0, text_similarity_threshold=0.35)

    rep1 = {
        "id": 1,
        "type": "flood",
        "description": "Severe road waterlogging near Andheri subway underpass traffic blocked",
        "latitude": 19.1197,
        "longitude": 72.8468,
    }
    rep2 = {
        "id": 2,
        "type": "flood",
        "description": "Andheri subway completely flooded with 3 feet water vehicles stuck",
        "latitude": 19.1201,  # ~60m away
        "longitude": 72.8471,
    }
    rep_distant = {
        "id": 3,
        "type": "flood",
        "description": "Severe road waterlogging near Chembur highway",
        "latitude": 19.0550,  # ~12km away
        "longitude": 72.8900,
    }
    rep_diff_type = {
        "id": 4,
        "type": "fire",
        "description": "Severe fire in transformer near Andheri subway underpass",
        "latitude": 19.1197,
        "longitude": 72.8468,
    }

    # Direct pairwise duplicate check (spatial proximity < 100m flags candidate)
    is_dup, orig_id, score = detector.is_duplicate(rep2, [rep1, rep_distant, rep_diff_type])
    assert is_dup is True
    assert orig_id == 1
    assert score > 0.10

    # Semantic text overlap test
    rep_text_similar = {
        "id": 5,
        "type": "flood",
        "description": "Severe road waterlogging near Andheri subway underpass traffic blocked completely",
        "latitude": 19.1198,
        "longitude": 72.8469,
    }
    is_dup_text, orig_id_text, score_text = detector.is_duplicate(rep_text_similar, [rep1])
    assert is_dup_text is True
    assert orig_id_text == 1
    assert score_text > 0.60

    # Multi-report clustering
    reports = [rep1, rep2, rep_distant, rep_diff_type]
    clusters = detector.cluster_reports(reports)
    assert len(clusters) >= 3  # Cluster 1 (rep1 + rep2), Cluster 2 (distant), Cluster 3 (diff type)

    # Find the duplicate cluster
    dup_cluster = [c for c in clusters if c["is_duplicate_group"]][0]
    assert dup_cluster["member_count"] == 2
    assert set(dup_cluster["report_ids"]) == {1, 2}
    assert dup_cluster["radius_meters"] < 200.0


def test_report_confidence_scorer_explainable():
    """Verifies multi-signal explainable confidence scoring."""
    # 1. High credibility report: valid coordinates, detailed text, media attached, sensor active
    high_eval = ReportConfidenceScorer.evaluate_confidence(
        description="Flash flood in low-lying residential colony near Milan subway. Water entering ground floor premises and electrical sub-station.",
        latitude=19.098,
        longitude=72.843,  # Mumbai Suburban
        has_media=True,
        corroborating_reports_count=3,
        nearby_sensor_active=True,
        rainfall_observed_mm=62.0,
    )
    assert high_eval["confidence_level"] == "HIGH"
    assert high_eval["confidence_score"] >= 0.80
    assert len(high_eval["contributing_factors"]) >= 5
    assert any(f["signal"] == "photographic_evidence" and f["delta"] > 0 for f in high_eval["contributing_factors"])
    assert any(f["signal"] == "sensor_consistency" and f["delta"] > 0 for f in high_eval["contributing_factors"])

    # 2. Low credibility report: short text, no media, unverified coordinates
    low_eval = ReportConfidenceScorer.evaluate_confidence(
        description="flood here",
        latitude=0.0,
        longitude=0.0,
        has_media=False,
    )
    assert low_eval["confidence_level"] == "LOW"
    assert low_eval["confidence_score"] < 0.45
    assert any(f["signal"] == "geographic_validity" and f["delta"] < 0 for f in low_eval["contributing_factors"])
    assert any(f["signal"] == "text_completeness" and f["delta"] < 0 for f in low_eval["contributing_factors"])


def test_ml_baseline_training_and_evaluation():
    """Verifies scikit-learn ML baseline training, evaluation metrics, and feature importances."""
    baseline = MLRiskBaseline()
    metrics = baseline.train_and_evaluate()

    # Dataset documentation
    ds = metrics["dataset_summary"]
    assert ds["total_samples"] == 600
    assert ds["train_samples"] == 480  # 80%
    assert ds["test_samples"] == 120   # 20%
    assert "class_distribution" in ds
    assert len(ds["class_distribution"]) == 4

    # Performance metrics
    rf = metrics["random_forest_metrics"]
    assert rf["accuracy"] >= 0.85
    assert rf["macro_f1"] >= 0.80
    assert rf["weighted_f1"] >= 0.80
    assert "confusion_matrix" in rf
    assert len(rf["confusion_matrix"]["matrix"]) == 4  # 4x4 matrix

    # Feature importances
    fi = metrics["feature_importances"]
    assert len(fi) == len(FeatureExtractor.FEATURE_NAMES)
    top_feature = fi[0]["feature"]
    assert "rainfall" in top_feature or "overflow" in top_feature or "water_level" in top_feature

    # Single prediction
    pred = baseline.predict_risk({
        "rainfall_1h_mm": 55.0,
        "rainfall_24h_mm": 150.0,
        "rainfall_72h_mm": 200.0,
        "water_level_meters": 5.0,
        "river_overflow_delta": 0.5,
        "river_has_gauge": True,
        "avg_slope_deg": 12.0,
        "max_slope_deg": 30.0,
        "soil_saturation_pct": 80.0,
        "historical_flood_risk": 0.9,
        "historical_landslide_risk": 0.5,
    })
    assert pred["predicted_risk_level"] in ["HIGH", "CRITICAL"]
    assert "probabilities" in pred
    assert pred["isOfficialWarning"] is False


def test_intelligence_fastapi_endpoints(client: TestClient):
    """Verifies all FastAPI /api/v1/intelligence routes."""
    # 1. Flood risk endpoint
    flood_res = client.get("/api/v1/intelligence/risk/flood?rainfall_1h_mm=60.0&rainfall_24h_mm=130.0&district_id=2")
    assert flood_res.status_code == 200
    f_data = flood_res.json()
    assert f_data["hazardType"] == "FLOOD"
    assert f_data["riskLevel"] in ["HIGH", "CRITICAL"]
    assert f_data["isOfficialWarning"] is False
    assert "disclaimer" in f_data

    # 2. Landslide risk endpoint
    landslide_res = client.get("/api/v1/intelligence/risk/landslide?rainfall_72h_mm=260.0&rainfall_24h_mm=80.0&district_id=5")
    assert landslide_res.status_code == 200
    l_data = landslide_res.json()
    assert l_data["hazardType"] == "LANDSLIDE"
    assert l_data["riskLevel"] in ["HIGH", "CRITICAL"]
    assert l_data["isOfficialWarning"] is False

    # 3. District multi-hazard indicative risk
    dist_res = client.get("/api/v1/intelligence/risk/district/2")
    assert dist_res.status_code == 200
    d_data = dist_res.json()
    assert "composite_risk_level" in d_data
    assert "hazards" in d_data
    assert "flood" in d_data["hazards"]
    assert "landslide" in d_data["hazards"]
    assert "ml_comparative_baseline" in d_data

    # 4. Confidence evaluation endpoint
    conf_payload = {
        "description": "Severe street inundation near Kurla station with stalled public buses",
        "latitude": 19.065,
        "longitude": 72.879,
        "has_media": True,
        "user_role": "citizen",
        "corroborating_reports_count": 2,
        "nearby_sensor_active": True,
    }
    conf_res = client.post("/api/v1/intelligence/confidence/evaluate", json=conf_payload)
    assert conf_res.status_code == 200
    c_data = conf_res.json()
    assert c_data["confidence_level"] in ["MEDIUM", "HIGH"]
    assert "contributing_factors" in c_data

    # 5. ML benchmark metrics endpoint
    ml_res = client.get("/api/v1/intelligence/ml/benchmark")
    assert ml_res.status_code == 200
    m_data = ml_res.json()
    assert "random_forest_metrics" in m_data
    assert "feature_importances" in m_data
    assert "dataset_summary" in m_data
    assert m_data["random_forest_metrics"]["accuracy"] > 0.85
