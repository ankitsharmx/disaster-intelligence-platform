"""
Duplicate Report Detection & Spatio-Temporal Clustering Module.
Combines Haversine geographic distance, elapsed time windows, hazard categories,
and scikit-learn TF-IDF semantic cosine similarity.

Policy: Identified duplicate candidates are grouped for officer review, never auto-deleted.
"""
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
        max_distance_meters: float = 500.0,
        max_time_delta_seconds: float = 7200.0,  # 2 hours
        text_similarity_threshold: float = 0.35,
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
            # Fallback to proximity
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
            return round(float(sim), 3)
        except Exception:
            return 0.0

    def cluster_reports(
        self,
        reports: List[Dict[str, Any]],
        distance_threshold_m: Optional[float] = None,
        time_threshold_sec: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Groups a list of incident reports into suspected duplicate clusters.
        Returns a list of cluster summaries for officer queue review:
        [
          {
            "cluster_id": 1,
            "primary_report_id": 10,
            "type": "flood",
            "member_count": 3,
            "report_ids": [10, 11, 14],
            "avg_similarity": 0.65,
            "centroid": [19.119, 72.846],
            "radius_meters": 142.5
          }
        ]
        """
        dist_thresh = distance_threshold_m or self.max_distance_meters
        time_thresh = time_threshold_sec or self.max_time_delta_seconds

        if not reports:
            return []

        clusters: List[List[Dict[str, Any]]] = []
        visited = set()

        for i, rep in enumerate(reports):
            if rep["id"] in visited:
                continue

            current_cluster = [rep]
            visited.add(rep["id"])

            for j, cand in enumerate(reports):
                if cand["id"] in visited or cand["id"] == rep["id"]:
                    continue

                if cand.get("type") != rep.get("type"):
                    continue

                # Time delta check
                t1 = rep.get("created_at")
                t2 = cand.get("created_at")
                if t1 and t2:
                    delta = abs((t1 - t2).total_seconds())
                    if delta > time_thresh:
                        continue

                # Distance check
                d_km = GeographyService.calculate_haversine_distance_km(
                    rep["latitude"], rep["longitude"], cand["latitude"], cand["longitude"]
                )
                d_m = d_km * 1000.0

                if d_m <= dist_thresh:
                    # Text similarity check
                    sim = self.calculate_similarity(rep.get("description", ""), cand.get("description", ""))
                    if sim >= self.text_similarity_threshold or d_m < 150.0:
                        current_cluster.append(cand)
                        visited.add(cand["id"])

            clusters.append(current_cluster)

        # Build output structure
        cluster_results = []
        for idx, cl in enumerate(clusters):
            primary = cl[0]
            lats = [r["latitude"] for r in cl]
            lons = [r["longitude"] for r in cl]
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)

            max_r_m = 0.0
            for r in cl:
                d_km = GeographyService.calculate_haversine_distance_km(center_lat, center_lon, r["latitude"], r["longitude"])
                max_r_m = max(max_r_m, d_km * 1000.0)

            cluster_results.append({
                "cluster_id": idx + 1,
                "primary_report_id": primary["id"],
                "type": primary.get("type"),
                "member_count": len(cl),
                "is_duplicate_group": len(cl) > 1,
                "report_ids": [r["id"] for r in cl],
                "centroid": [round(center_lat, 5), round(center_lon, 5)],
                "radius_meters": round(max_r_m, 1),
                "sample_descriptions": [r.get("description", "")[:80] for r in cl[:3]],
            })

        return cluster_results


duplicate_detector = DuplicateDetector()
