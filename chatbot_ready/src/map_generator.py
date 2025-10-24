# src/map_generator.py
import folium
import pandas as pd
from typing import List, Dict, Any
from collections import defaultdict


class MapGenerator:
    """
    Simple point map generator for SF film locations.
    Only creates maps - doesn't analyze or interpret data.
    """
    
    def __init__(self):
        self.default_center = [37.7749, -122.4194]  # SF coordinates
    
    def create_point_map(self, location_data: List[Dict], 
                         title: str = "SF Film Locations") -> folium.Map:
        """
        Create a simple point map from standardized location data.
        ✅ IMPROVED: Groups multiple films at the same location
        
        Args:
            location_data: List of dicts with 'location_name', 'geometry', 'metadata'
            title: Map title
            
        Returns:
            folium.Map object
        """
        if not location_data:
            return self._create_empty_map(title)
        
        # ✅ Group locations by name (handle duplicate locations from multiple films)
        grouped_locations = self._group_by_location(location_data)
        
        # Force SF center
        sf_center = [37.7749, -122.4194]
        
        # Create map
        m = folium.Map(location=sf_center, zoom_start=13)       
       
        # Add markers for each unique location
        for loc_name, loc_info in grouped_locations.items():
            geom = loc_info['geometry']
            films = loc_info['films']
            
            # Build popup with nice formatting
            popup_html = f"<b>{loc_name}</b><br><br>"
            
            # If multiple films at this location, show them nicely
            if len(films) > 1:
                popup_html += f"🎬 <b>Featured in {len(films)} films:</b><br><br>"
                for i, film in enumerate(films, 1):
                    popup_html += f"<b>Film {i}:</b> {film['film_title']} ({film['year']})<br>"
            else:
                # Single film
                film = films[0]
                popup_html += f"🎬 <b>Film:</b> {film['film_title']}<br>"
                popup_html += f"📅 <b>Year:</b> {film['year']}<br>"
            
            folium.Marker(
                location=[geom.y, geom.x],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=loc_name,
                icon=folium.Icon(color='red', icon='film', prefix='fa')
            ).add_to(m)
        
        # Add title
        unique_location_count = len(grouped_locations)
        title_html = f'''
        <div style="position: fixed; 
                    top: 10px; left: 50px; right: 50px; 
                    z-index:9999; 
                    background-color:white;
                    border:2px solid grey;
                    border-radius: 5px;
                    padding: 10px;
                    text-align: center;">
            <h3 style="margin:0;">{title}</h3>
            <p style="margin:5px 0 0 0; font-size:14px; color:#666;">
                {unique_location_count} unique location{'' if unique_location_count == 1 else 's'} found
            </p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))
        
        return m
    
    def _group_by_location(self, location_data: List[Dict]) -> Dict[str, Dict]:
        """
        Group location data by location name to handle multiple films at same location.
        
        Args:
            location_data: List of location dicts with metadata
            
        Returns:
            Dict mapping location_name to {geometry, films: [film_info, ...]}
        """
        grouped = defaultdict(lambda: {'geometry': None, 'films': []})
        
        for loc in location_data:
            loc_name = loc['location_name']
            
            # Store geometry (should be same for all instances of this location)
            if grouped[loc_name]['geometry'] is None:
                grouped[loc_name]['geometry'] = loc['geometry']
            
            # Add film info to this location
            metadata = loc.get('metadata', {})
            
            # Extract film information from metadata
            film_info = {
                'film_title': metadata.get('film_title', metadata.get('title', 'Unknown')),
                'year': metadata.get('year', 'Unknown')
            }
            
            # Only add if not already present (avoid duplicates)
            if film_info not in grouped[loc_name]['films']:
                grouped[loc_name]['films'].append(film_info)
        
        return dict(grouped)
    
    def _create_empty_map(self, title: str) -> folium.Map:
        """Create fallback map when no locations found"""
        m = folium.Map(location=self.default_center, zoom_start=12)
        
        title_html = f'''
        <div style="position: fixed; 
                    top: 10px; left: 50px; right: 50px; 
                    z-index:9999; 
                    background-color:#fff3cd;
                    border:2px solid #ffc107;
                    border-radius: 5px;
                    padding: 10px;
                    text-align: center;">
            <h3 style="margin:0; color:#856404;">{title}</h3>
            <p style="margin:5px 0 0 0; color:#856404;">No locations found to display</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))
        
        return m