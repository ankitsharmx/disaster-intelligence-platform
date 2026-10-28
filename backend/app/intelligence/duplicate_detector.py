from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.services.geography_service import GeographyService


class DuplicateDetector:
    """
    Identifies duplicate incident reports using spatial distance,
    temporal proximity, and TF-IDF semantic textual similarity.
    """

    def __init__(
        self,
        max_distance_meters: float = 400.0,
        max_time_delta_seconds: float = 3600.0,  # 1 hour
        text_similarity_threshold: float = 0.40,
    ):
        self.max_distance_meters = max_distance_meters
        self.max_time_delta_seconds = max_time_delta_seconds
        self.text_similarity_threshold = text_similarity_threshold

    def is_duplicate(
        self,
        new_report: Dict[str, Any],
        candidate_reports: List[Dict[str, Any]],
    ) -> Tuple[bool, Optional[int], float]:
        """
        Evaluates new_report against candidate_reports.
        Returns (is_duplicate: bool, original_report_id: Optional[int], match_score: float)
        """
        if not candidate_reports:
            return False, None, 0.0

        new_lat = new_report["latitude"]
        new_lon = new_report["longitude"]
        new_type = new_report.get("type")
        new_time = new_report.get("created_at") or datetime.now(timezone.utc)
        new_desc = new_report.get("description", "")

        candidates_filtered = []
        for cand in candidate_reports:
            # Check hazard type compatibility
            if cand.get("type") != new_type:
                continue

            # Check temporal window
            cand_time = cand.get("created_at")
            if cand_time:
                delta = abs((new_time - cand_time).total_seconds())
                if delta > self.max_time_delta_seconds:
                    continue

            # Check spatial distance (Haversine)
            dist_km = GeographyService.calculate_haversine_distance_km(
                new_lat, new_lon, cand["latitude"], cand["longitude"]
            )
            dist_meters = dist_km * 1000.0

            if dist_meters <= self.max_distance_meters:
                candidates_filtered.append((cand, dist_meters))

        if not candidates_filtered:
            return False, None, 0.0

        # Calculate text similarity with scikit-learn TF-IDF
        corpus = [new_desc] + [c[0].get("description", "") for c in candidates_filtered]
        
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            tfidf_matrix = vectorizer.fit_transform(corpus)
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

            best_idx = int(np.argmax(similarities))
            best_score = float(similarities[best_idx])
            best_candidate, dist_m = candidates_filtered[best_idx]

            # High spatial proximity + positive text overlap = duplicate
            if best_score >= self.text_similarity_threshold or dist_m < 100.0:
                return True, best_candidate.get("id"), round(best_score, 3)

        except Exception:
            # If TF-IDF encounters empty vocabulary, fallback to spatial proximity
            best_candidate, dist_m = candidates_filtered[0]
            if dist_m < 150.0:
                return True, best_candidate.get("id"), 0.5

        return False, None, 0.0

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculates TF-IDF cosine similarity between two text descriptions."""
        if not text1 or not text2:
            return 0.0
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            tfidf_matrix = vectorizer.fit_transform([text1, text2])
            sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(round(sim, 3))
        except Exception:
            return 0.0


duplicate_detector = DuplicateDetector()
