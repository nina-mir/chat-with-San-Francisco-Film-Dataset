# src/map_generator.py
import folium
import pandas as pd
from typing import List, Dict, Any


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
        
        Args:
            location_data: List of dicts with 'location_name', 'geometry', 'metadata'
            title: Map title
            
        Returns:
            folium.Map object
        """
        if not location_data:
            return self._create_empty_map(title)
        
        # Calculate center from data
        lats = [loc['geometry'].y for loc in location_data]
        lons = [loc['geometry'].x for loc in location_data]
        center = [sum(lats)/len(lats), sum(lons)/len(lons)]
        
        # Create map
        m = folium.Map(location=center, zoom_start=13)
        
        # Add markers
        for loc_data in location_data:
            geom = loc_data['geometry']
            metadata = loc_data.get('metadata', {})
            
            # Build popup with nice formatting
            popup_html = f"<b>{loc_data['location_name']}</b><br><br>"
            
            # Add metadata (filter out None/NaN values)
            for key, val in metadata.items():
                if pd.notna(val) and val != '' and val != 'None':
                    # Capitalize key for display
                    display_key = key.replace('_', ' ').title()
                    popup_html += f"<b>{display_key}:</b> {val}<br>"
            
            folium.Marker(
                location=[geom.y, geom.x],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=loc_data['location_name'],
                icon=folium.Icon(color='red', icon='film', prefix='fa')
            ).add_to(m)
        
        # Add title
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
                {len(location_data)} location{'' if len(location_data) == 1 else 's'} found
            </p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))
        
        return m
    
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