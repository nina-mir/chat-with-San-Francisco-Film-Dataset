"""
Map HTML Embedding Module

This module provides functionality to embed Folium map visualizations and query results
into custom HTML documents for easy sharing and presentation.

The main function combines user queries, execution results, and interactive maps into
a single HTML file that can be opened in any web browser.

Key Features:
- Embeds Folium map HTML representations into custom-styled pages
- Includes query metadata and detailed results in formatted JSON
- Automatically generates timestamped HTML files
- Handles file creation with proper error handling

Example:
    >>> from src.map_embedder import embed_in_custom_html
    >>> user_query = "film locations in San Francisco"
    >>> execution_result = {
    ...     'summary': 'Found 25 film locations',
    ...     'data': {'locations': [...]}
    ... }
    >>> map_html = folium_map._repr_html_()
    >>> embed_in_custom_html(user_query, execution_result, map_html)
    # Creates 'maps/results_with_map_1700000000.html'

Note:
    Requires the 'maps' directory to be writable. The function will create the
    directory if it doesn't exist.
"""

import json
from pathlib import Path
import time
from typing import Dict, Any
from src.logger import convert_shapely_to_serializable




style_string = """
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 
                        "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            margin: 20px;
            background-color: #f8f9fa;
            color: #333;
        }
        
        h1, h2 {
            font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
            font-weight: 600;
            color: #2c3e50;
        }
        
        #query-info {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        #map-container {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        #results {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        pre {
            font-family: "SF Mono", "Monaco", "Inconsolata", monospace;
            font-size: 14px;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
        }
    """


def embed_in_custom_html(user_query: str, execution_result: Dict[str, Any], map_html: str) -> None:
    """
    Embed query results and Folium map into a custom HTML document.
    
    Creates a self-contained HTML file that displays:
    - The original user query
    - A summary of the execution results  
    - An interactive Folium map visualization
    - Detailed results in formatted JSON
    
    Args:
        user_query (str): The original search query from the user
        execution_result (Dict[str, Any]): Dictionary containing query results with 
            expected keys:
            - 'summary': Brief description of results (optional)
            - 'data': Detailed results data for JSON display (optional)
        map_html (str): HTML string representation of a Folium map object,
            typically generated using map_obj._repr_html_()
    
    Returns:
        None: The function saves an HTML file to disk but returns nothing
    
    Side Effects:
        - Creates a timestamped HTML file in the 'maps/' directory
        - Creates the 'maps/' directory if it doesn't exist
        - Prints error messages to stdout if file operations fail
    
    Raises:
        OSError: If the file cannot be written due to filesystem issues
        Exception: For any other unexpected errors during file operations
    
    Example:
        >>> result = {
        ...     'summary': 'Found 15 locations',
        ...     'data': {'locations': [{'name': 'Golden Gate Bridge', ...}]}
        ... }
        >>> embed_in_custom_html(
        ...     "movie filming locations",
        ...     result,
        ...     map._repr_html_()
        ... )
    """

    # Use your existing converter to handle both Shapely objects AND DataFrames
    
    # Convert any non-serializable objects in execution_result
    serializable_result = convert_shapely_to_serializable(execution_result)



    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SF Film Locations Map</title>
        <meta charset="utf-8">
        <style>
           {style_string}
        </style>
    </head>
    <body>
        <h1>Query Results</h1>
        <div id="query-info">
            <p><strong>Query:</strong> {user_query}</p>
            <p><strong>Summary:</strong> {serializable_result.get('summary')}</p>
        </div>
        
        <div id="map-container">
            {map_html}
        </div>
        
        <div id="results">
            <h2>Detailed Results</h2>
            <pre>{json.dumps(serializable_result.get('data'), indent=2)}</pre>
        </div>
    </body>
    </html>
    """

    # Save it
    try:
        # Create directory and file path
        maps_dir = Path('maps')
        maps_dir.mkdir(exist_ok=True)  # Create directory if it doesn't exist
        
        map_filename = f'results_with_map{int(time.time())}.html'
        map_file_path = maps_dir / map_filename  # Full path to the HTML file
        
        with open(map_file_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        print(f"✓ Map saved to: {map_file_path}")
    except Exception as e:
        print(f'Error in map_embed_in_html module: {e}')

    return None