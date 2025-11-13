"""
Geospatial utilities for point-in-polygon checks and GeoJSON processing
"""
import json
import os
from typing import List, Tuple, Optional, Dict
from pathlib import Path


def point_in_polygon(point: Tuple[float, float], polygon: List[List[float]]) -> bool:
    """
    Check if a point is inside a polygon using the ray casting algorithm.
    
    Args:
        point: Tuple of (longitude, latitude) - note: GeoJSON uses [lng, lat]
        polygon: List of [lng, lat] coordinate pairs forming a closed polygon
        
    Returns:
        True if point is inside polygon, False otherwise
    """
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside


def point_in_multipolygon(point: Tuple[float, float], multipolygon: List[List[List[List[float]]]]) -> bool:
    """
    Check if a point is inside any polygon in a MultiPolygon.
    
    Args:
        point: Tuple of (longitude, latitude)
        multipolygon: GeoJSON MultiPolygon structure (list of polygons, each with exterior and holes)
        
    Returns:
        True if point is inside any polygon
    """
    for polygon_group in multipolygon:
        # First ring is exterior, rest are holes
        if polygon_group and len(polygon_group) > 0:
            exterior = polygon_group[0]
            if point_in_polygon(point, exterior):
                # Check if point is in any hole (if so, it's outside)
                in_hole = False
                for hole in polygon_group[1:]:
                    if point_in_polygon(point, hole):
                        in_hole = True
                        break
                if not in_hole:
                    return True
    return False


class GeoJSONRegionMapper:
    """
    Loads GeoJSON file and provides point-in-region lookup functionality.
    """
    
    def __init__(self, geojson_path: str, region_mapping: Dict[str, str]):
        """
        Initialize the mapper with GeoJSON file and region mapping.
        
        Args:
            geojson_path: Path to the GeoJSON file
            region_mapping: Dictionary mapping regional district names to high-level regions
        """
        self.region_mapping = region_mapping
        self.geojson_path = geojson_path
        self.features_by_region: Dict[str, List[Dict]] = {}
        self._load_geojson()
    
    def _load_geojson(self):
        """Load and process the GeoJSON file."""
        try:
            # Get absolute path
            if not os.path.isabs(self.geojson_path):
                # Try relative to project root
                project_root = Path(__file__).parent.parent.parent
                geojson_path = project_root / self.geojson_path
            else:
                geojson_path = Path(self.geojson_path)
            
            with open(geojson_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            # Group features by high-level region
            for feature in geojson_data.get('features', []):
                props = feature.get('properties', {})
                district_name = props.get('ADMIN_AREA_NAME', '')
                
                # Map district to high-level region
                high_level_region = self.region_mapping.get(district_name)
                if high_level_region:
                    if high_level_region not in self.features_by_region:
                        self.features_by_region[high_level_region] = []
                    self.features_by_region[high_level_region].append(feature)
            
            print(f"Loaded GeoJSON: {len(geojson_data.get('features', []))} features mapped to {len(self.features_by_region)} regions")
            
        except FileNotFoundError:
            print(f"Warning: GeoJSON file not found at {geojson_path}. Using fallback text matching.")
            self.features_by_region = {}
        except Exception as e:
            print(f"Error loading GeoJSON: {e}. Using fallback text matching.")
            self.features_by_region = {}
    
    def get_region_for_point(self, lat: float, lng: float) -> Optional[str]:
        """
        Determine which high-level region a point belongs to.
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            High-level region name or None if not found
        """
        point = (lng, lat)  # GeoJSON uses [lng, lat] order
        
        for region_name, features in self.features_by_region.items():
            for feature in features:
                geometry = feature.get('geometry', {})
                geom_type = geometry.get('type')
                coordinates = geometry.get('coordinates')
                
                if not coordinates:
                    continue
                
                is_inside = False
                
                if geom_type == 'Polygon':
                    # Polygon: coordinates is [[exterior], [hole1], [hole2], ...]
                    if point_in_polygon(point, coordinates[0]):
                        # Check if point is in any hole
                        in_hole = False
                        for hole in coordinates[1:]:
                            if point_in_polygon(point, hole):
                                in_hole = True
                                break
                        if not in_hole:
                            is_inside = True
                
                elif geom_type == 'MultiPolygon':
                    # MultiPolygon: coordinates is [[[exterior], [hole]], [[exterior2], [hole2]], ...]
                    is_inside = point_in_multipolygon(point, coordinates)
                
                if is_inside:
                    return region_name
        
        return None
    
    def has_geojson_data(self) -> bool:
        """Check if GeoJSON data was successfully loaded."""
        return len(self.features_by_region) > 0


