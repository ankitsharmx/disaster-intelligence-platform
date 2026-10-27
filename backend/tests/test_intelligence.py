from datetime import datetime, timezone, timedelta
from app.intelligence.rules import RiskRuleEngine
from app.intelligence.scoring import ConfidenceScorer
from app.intelligence.duplicate_detector import DuplicateDetector


def test_risk_rules_rainfall():
    # Low risk
    low = RiskRuleEngine.evaluate_rainfall(10.0)
    assert low["level"] == "low"

    # Medium risk
    med = RiskRuleEngine.evaluate_rainfall(35.0)
    assert med["level"] == "medium"

    # High risk
    high = RiskRuleEngine.evaluate_rainfall(60.0)
    assert high["level"] == "high"

    # Critical risk
    crit = RiskRuleEngine.evaluate_rainfall(95.0)
    assert crit["level"] == "critical"


def test_confidence_scoring():
    # Short text from citizen
    score_low = ConfidenceScorer.calculate_score("water everywhere")
    assert score_low < 0.5

    # Detailed text with media and officer role
    score_high = ConfidenceScorer.calculate_score(
        description="Milan subway completely submerged under 4 feet of fast flowing water with 3 trapped vehicles.",
        has_media=True,
        user_role="officer",
        nearby_sensor_corroboration=True,
    )
    assert score_high >= 0.85


def test_duplicate_detection():
    now = datetime.now(timezone.utc)
    detector = DuplicateDetector(max_distance_meters=500.0, max_time_delta_seconds=1800)

    existing_reports = [
        {
            "id": 101,
            "type": "flood",
            "description": "Severe flooding at Milan Subway, cars stranded and water level rising rapidly.",
            "latitude": 19.0885,
            "longitude": 72.8432,
            "created_at": now - timedelta(minutes=10),
        }
    ]

    # Similar incoming report in same subway location
    incoming_duplicate = {
        "type": "flood",
        "description": "Milan Subway is flooded, multiple cars stuck in high water level.",
        "latitude": 19.0888,
        "longitude": 72.8430,
        "created_at": now,
    }

    is_dup, orig_id, sim = detector.is_duplicate(incoming_duplicate, existing_reports)
    assert is_dup is True
    assert orig_id == 101

    # Completely different report in different location
    distant_report = {
        "type": "flood",
        "description": "Water logging near Dadar station market.",
        "latitude": 19.0178,
        "longitude": 72.8478,
        "created_at": now,
    }

    is_dup_diff, _, _ = detector.is_duplicate(distant_report, existing_reports)
    assert is_dup_diff is False
