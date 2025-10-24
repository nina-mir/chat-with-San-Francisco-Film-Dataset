# src/map_analyzer.py
import pandas as pd
import geopandas as gpd
from typing import List, Dict, Any, Optional


class MapDataAnalyzer:
    """
    Analyzes execution results to determine if mapping is possible.
    Probes data structures to detect location references.
    No AI calls - just structural analysis and location matching.
    """
    
    def __init__(self, gdf: gpd.GeoDataFrame):
        self.gdf = gdf
        self._create_location_lookup()
    
    def _create_location_lookup(self):
        """Build location_name -> geometry dict"""
        self.location_map = {}
        for _, row in self.gdf.iterrows():
            if pd.notna(row['Locations']) and pd.notna(row.geometry):
                self.location_map[row['Locations']] = {
                    'geometry': row.geometry,
                    'title': row.get('Title'),
                    'year': row.get('Year')
                }
    
    def analyze(self, execution_result: Dict[str, Any], 
                user_query: str) -> Dict[str, Any]:
        """
        Analyze if execution result contains mappable data.
        
        Returns:
            {
                'can_map': bool,
                'reason': str,
                'location_data': List[Dict] or None,
                'location_mentioned': bool,
                'data_type': str
            }
        """
        data = execution_result.get('data')

        # DEBUG: Print what is being analyzed
        print(f"🔍 ANALYZER: data type = {type(data)}")
        if isinstance(data, list) and data:
            print(f"🔍 ANALYZER: list with {len(data)} items")
            print(f"🔍 ANALYZER: first item = {data[0]}")
            
        # Check if query mentions locations
        location_keywords = ['location', 'locations', 'place', 'places', 'where', 'map', 'filmed', 'shot']
        query_lower = user_query.lower()
        location_mentioned = any(kw in query_lower for kw in location_keywords)
        
        # Initialize result
        result = {
            'can_map': False,
            'reason': '',
            'location_data': None,
            'location_mentioned': location_mentioned,
            'data_type': self._get_data_type(data)
        }
        
        # Quick checks for non-mappable data
        if data is None:
            result['reason'] = "No data in execution result"
            return result
        
        # Scalar values (int, float, str, bool) - not mappable
        if isinstance(data, (int, float, str, bool)):
            result['reason'] = f"Data is scalar ({type(data).__name__}), not mappable"
            return result
        
        # Try to extract locations
        extracted = self._extract_locations(data)
        
        if extracted:
            result['can_map'] = True
            result['location_data'] = extracted
            result['reason'] = f"Found {len(extracted)} mappable locations"
        else:
            result['reason'] = "No location data found in result"
        
        return result
    
    def _get_data_type(self, data: Any) -> str:
        """Get human-readable data type description"""
        if data is None:
            return "None"
        if isinstance(data, gpd.GeoDataFrame):
            return "GeoDataFrame"
        if isinstance(data, pd.DataFrame):
            return "DataFrame"
        if isinstance(data, dict):
            return "Dict"
        if isinstance(data, list):
            return "List"
        return type(data).__name__
    
    def _get_field_case_insensitive(self, item: dict, field_names: list, default=None):
        """
        Get a field from dict using case-insensitive lookup.
        
        Args:
            item: Dictionary to search
            field_names: List of possible field names (e.g., ['title', 'Title', 'TITLE'])
            default: Default value if not found
            
        Returns:
            Field value or default
        """
        # Create a case-insensitive lookup
        lower_to_original = {k.lower(): k for k in item.keys()}
        
        # Try each field name (case-insensitive)
        for field in field_names:
            field_lower = field.lower()
            if field_lower in lower_to_original:
                return item[lower_to_original[field_lower]]
        
        return default
    
    def _extract_locations(self, data: Any) -> Optional[List[Dict]]:
        """
        Extract location information from various data structures.
        Uses probing to detect if values are location names.
        
        Returns standardized list of location dicts or None.
        """
        # Case 1: GeoDataFrame (has geometry already)
        if isinstance(data, gpd.GeoDataFrame):
            return self._from_geodataframe(data)
        
        # Case 2: List (could be list of location names)
        if isinstance(data, list):
            return self._from_list(data)
        
        # Case 3: Dict (could be various formats)
        if isinstance(data, dict):
            return self._from_dict(data)
        
        # Case 4: DataFrame
        if isinstance(data, pd.DataFrame):
            return self._from_dataframe(data)
        
        return None
    
    def _is_location_name(self, value: Any) -> bool:
        """Check if a value is a known location name"""
        if not isinstance(value, str):
            return False
        return value in self.location_map
    
    def _probe_list_for_locations(self, data: list, sample_size: int = 5) -> bool:
        """
        Probe first N items in list to see if they're location names.
        Returns True if at least one item matches a known location.
        """
        if not data:
            return False
        
        # Sample first few items
        sample = data[:min(sample_size, len(data))]
        
        for item in sample:
            if self._is_location_name(item):
                return True
        
        return False
    
    def _from_geodataframe(self, gdf: gpd.GeoDataFrame) -> Optional[List[Dict]]:
        """Extract from GeoDataFrame - already has geometry"""
        locations = []
        for _, row in gdf.iterrows():
            if pd.notna(row.geometry):
                locations.append({
                    'location_name': row.get('Locations', 'Unknown'),
                    'geometry': row.geometry,
                    'metadata': {
                        'title': row.get('Title'),
                        'year': row.get('Year')
                    }
                })
        return locations if locations else None
    
    def _from_list(self, data: list) -> Optional[List[Dict]]:
        """
        Extract from list - could be:
        1. List of location name strings ['Union Square', 'Golden Gate Bridge']
        2. List of dicts with location info
        """
        if not data:
            return None
        
        # Check first item type
        first_item = data[0]
        
        # Case 1: List of strings - probe if they're locations
        if isinstance(first_item, str):
            if self._probe_list_for_locations(data):
                locations = []
                for loc_name in data:
                    if loc_name in self.location_map:
                        locations.append({
                            'location_name': loc_name,
                            'geometry': self.location_map[loc_name]['geometry'],
                            'metadata': {
                                'title': self.location_map[loc_name].get('title'),
                                'year': self.location_map[loc_name].get('year')
                            }
                        })
                return locations if locations else None
            return None
        
        # Case 2: List of dicts
        if isinstance(first_item, dict):
            return self._from_list_of_dicts(data)
        
        return None
    
    def _from_list_of_dicts(self, data: list) -> Optional[List[Dict]]:
        """
        Extract from list of dicts with location fields.
        ✅ IMPROVED: Case-insensitive field lookups + clean film metadata
        """
        locations = []
        for item in data:
            # Look for location field (case-insensitive)
            loc_value = None
            for key in item.keys():
                if key.lower() in ['locations', 'location', 'place']:
                    loc_value = item[key]
                    break
            
            # Handle both single location (string) and multiple locations (list)
            if loc_value:
                # Convert to list if it's a string
                loc_names = loc_value if isinstance(loc_value, list) else [loc_value]
                
                # Process each location name
                for loc_name in loc_names:
                    if isinstance(loc_name, str) and loc_name in self.location_map:
                        # ✅ Use case-insensitive field lookup
                        film_title = self._get_field_case_insensitive(
                            item, ['title', 'Title', 'film_title', 'Film_Title'], 'Unknown'
                        )
                        year = self._get_field_case_insensitive(
                            item, ['year', 'Year', 'release_year', 'Release_Year'], 'Unknown'
                        )
                        
                        # Create clean metadata with just film info
                        film_metadata = {
                            'film_title': film_title,
                            'year': year
                        }
                        
                        locations.append({
                            'location_name': loc_name,
                            'geometry': self.location_map[loc_name]['geometry'],
                            'metadata': film_metadata
                        })
        
        return locations if locations else None
    
    def _from_dict(self, data: dict) -> Optional[List[Dict]]:
        """
        Extract from dictionary by systematically checking all keys and values.
        """
        if not data:
            return None
        
        # Collect all potential location extraction strategies
        extraction_attempts = [
            self._try_extract_from_location_list_values,
            self._try_extract_from_location_keys,
            self._try_extract_from_named_location_fields,
        ]
        
        # Try each strategy in order
        for extract_func in extraction_attempts:
            result = extract_func(data)
            if result:
                return result
        
        return None
    
    def _try_extract_from_location_list_values(self, data: dict) -> Optional[List[Dict]]:
        """
        Check if any values are lists containing location names.
        Example: {'Least popular locations': ['Union Square', 'Pier 39']}
        """
        locations = []
        
        for key, value in data.items():
            if isinstance(value, list) and value:
                # Probe if this list contains locations
                if self._probe_list_for_locations(value):
                    for item in value:
                        if isinstance(item, str) and item in self.location_map:
                            locations.append({
                                'location_name': item,
                                'geometry': self.location_map[item]['geometry'],
                                'metadata': {
                                    'category': key,  # e.g., "Least popular locations"
                                    'title': self.location_map[item].get('title'),
                                    'year': self.location_map[item].get('year')
                                }
                            })
        
        return locations if locations else None
    
    def _try_extract_from_location_keys(self, data: dict) -> Optional[List[Dict]]:
        """
        Check if keys themselves are location names.
        Example: {'Union Square': 25, 'Golden Gate Bridge': 18}
        """
        location_keys = [k for k in data.keys() 
                         if isinstance(k, str) and self._is_location_name(k)]
        
        if not location_keys:
            return None
        
        locations = []
        for loc_name in location_keys:
            locations.append({
                'location_name': loc_name,
                'geometry': self.location_map[loc_name]['geometry'],
                'metadata': {'value': data[loc_name]}
            })
        
        return locations if locations else None
    
    def _try_extract_from_named_location_fields(self, data: dict) -> Optional[List[Dict]]:
        """
        Check if any keys are named 'location', 'locations', 'place', etc.
        Example: {'location': 'Union Square', 'count': 5}
        """
        location_field_names = ['location', 'locations', 'place', 'places', 'spot', 'site']
        
        for key, value in data.items():
            key_lower = str(key).lower()
            
            # Check if key name suggests it contains location data
            if any(field in key_lower for field in location_field_names):
                # Value could be a string or list
                if isinstance(value, str) and value in self.location_map:
                    metadata = {k: v for k, v in data.items() if k != key}
                    return [{
                        'location_name': value,
                        'geometry': self.location_map[value]['geometry'],
                        'metadata': metadata
                    }]
                elif isinstance(value, list):
                    return self._from_list(value)
        
        return None
    
    def _from_dataframe(self, df: pd.DataFrame) -> Optional[List[Dict]]:
        """Extract from DataFrame with location column"""
        # Look for location column (case-insensitive)
        loc_col = None
        for col in df.columns:
            if col.lower() in ['locations', 'location', 'place']:
                loc_col = col
                break
        
        if not loc_col:
            return None
        
        locations = []
        for _, row in df.iterrows():
            loc_name = row.get(loc_col)
            if loc_name and loc_name in self.location_map:
                locations.append({
                    'location_name': loc_name,
                    'geometry': self.location_map[loc_name]['geometry'],
                    'metadata': row.to_dict()
                })
        
        return locations if locations else None