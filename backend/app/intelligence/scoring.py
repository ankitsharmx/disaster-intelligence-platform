from typing import Optional, Dict, Any


class ConfidenceScorer:
    """Calculates verification confidence score (0.0 to 1.0) for citizen hazard reports."""

    @staticmethod
    def calculate_score(
        description: str,
        has_media: bool = False,
        user_role: str = "citizen",
        nearby_sensor_corroboration: bool = False,
    ) -> float:
        score = 0.5  # Base prior

        # Text quality / specificity
        length = len(description.strip())
        if length > 80:
            score += 0.15
        elif length > 30:
            score += 0.08
        else:
            score -= 0.10

        # Presence of photographic or video proof
        if has_media:
            score += 0.20

        # Officer or first responder submission
        if user_role in {"officer", "admin"}:
            score += 0.25

        # Sensor corroboration
        if nearby_sensor_corroboration:
            score += 0.15

        # Bound to [0.05, 1.00]
        return round(max(0.05, min(1.0, score)), 2)
