import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from shapely.geometry import Point, shape, Polygon, MultiPolygon
from shapely.ops import nearest_points
import math

# Earth radius in kilometers for Haversine distance
EARTH_RADIUS_KM = 6371.0


class GeographyService:
    """
    High-performance spatial service for district resolution, point-in-polygon queries,
    and facility proximity calculations using Shapely and PostGIS.
    """

    def __init__(self, geojson_path: Optional[str] = None):
        self._districts: List[Dict[str, Any]] = []
        self._parsed_polygons: List[Tuple[Dict[str, Any], Any]] = []
        
        if geojson_path:
            self.load_geojson(geojson_path)
        else:
            default_path = Path(__file__).resolve().parents[2] / "data" / "geo" / "districts.geojson"
            if default_path.exists():
                self.load_geojson(str(default_path))

    def load_geojson(self, file_path: str) -> None:
        """Load district features and prepare Shapely polygons."""
        path = Path(file_path)
        if not path.exists():
            return
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._districts = []
        self._parsed_polygons = []

        for feature in data.get("features", []):
            geom = shape(feature["geometry"])
            props = feature.get("properties", {})
            props["id"] = feature.get("id", props.get("id"))
            self._districts.append(props)
            self._parsed_polygons.append((props, geom))

    def resolve_district(self, lat: float, lon: float, tolerance: float = 1e-6) -> Optional[Dict[str, Any]]:
        """
        Resolves a coordinate (latitude, longitude) to its containing District.
        
        Handles:
        1. Points strictly inside polygon (contains).
        2. Points on the boundary edge or vertex (touches / intersects with epsilon buffer).
        3. Points outside all known boundaries (returns None).
        
        Note: GeoJSON & Shapely use (longitude, latitude) coordinate order.
        """
        point = Point(lon, lat)

        # 1. First pass: exact containment
        for props, geom in self._parsed_polygons:
            if geom.contains(point):
                return props

        # 2. Second pass: boundary cases (touches or intersects)
        for props, geom in self._parsed_polygons:
            if geom.touches(point) or geom.intersects(point):
                return props

        # 3. Third pass: tolerance buffer for floating-point precision on boundary lines
        if tolerance > 0:
            buffered_point = point.buffer(tolerance)
            for props, geom in self._parsed_polygons:
                if geom.intersects(buffered_point):
                    return props

        return None

    @staticmethod
    def calculate_haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates great-circle distance between two coordinates in kilometers."""
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return EARTH_RADIUS_KM * c


# Singleton instance
geography_service = GeographyService()
