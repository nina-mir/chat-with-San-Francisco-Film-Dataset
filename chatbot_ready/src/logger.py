import json
from pathlib import Path
import jsonlines
from datetime import datetime
import numpy as np
import pandas as pd
import geopandas as gpd  # to handle GeoPandaDatafram booo
from shapely.geometry import Point

def convert_shapely_to_serializable(obj):
    """
    Recursively convert Shapely objects and pandas DataFrames to serializable format.
    
    Args:
        obj: Any Python object that may contain Shapely geometries or DataFrames
        
    Returns:
        Object with Shapely geometries converted to GeoJSON-like dicts and
        DataFrames converted to dictionaries or lists of records
    """
    # ✅ NEW: Handle NumPy scalar types FIRST (before other checks)
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()  # Convert to native Python int/float
    elif isinstance(obj, np.ndarray):
        return obj.tolist()  # Convert numpy arrays to lists
    
    # Handle GeoDataFrame FIRST (before DataFrame check)
    # GeoDataFrame is a subclass of DataFrame, so this must come first
    if isinstance(obj, gpd.GeoDataFrame):
        if obj.empty:
            return {"_type": "GeoDataFrame", "data": [], "columns": list(obj.columns)}
        
        # Convert geometry column to serializable format
        df_copy = obj.copy()
        if 'geometry' in df_copy.columns:
            df_copy['geometry'] = df_copy['geometry'].apply(
                lambda geom: convert_shapely_to_serializable(geom) if geom is not None else None
            )
        
        return {
            "_type": "GeoDataFrame",
            "data": df_copy.to_dict('records'),
            "columns": list(obj.columns),
            "shape": obj.shape,
            "crs": str(obj.crs) if obj.crs else None
        }
    
    # Handle pandas DataFrame
    elif isinstance(obj, pd.DataFrame):
        if obj.empty:
            return {"_type": "DataFrame", "data": [], "columns": list(obj.columns)}
        # Convert to list of records (most common use case)
        return {
            "_type": "DataFrame",
            "data": df_copy.to_dict('records'),  # ⚠️ Note: you may need to recursively convert this too
            "columns": list(obj.columns),
            "shape": obj.shape
        }
    
    # Handle pandas Series
    elif isinstance(obj, pd.Series):
        return {
            "_type": "Series",
            "data": obj.to_dict(),
            "index": list(obj.index) if hasattr(obj.index, 'tolist') else str(obj.index),
            "dtype": str(obj.dtype)
        }
    
    # Handle Shapely Point
    elif isinstance(obj, Point):
        return {
            'type': 'Point',
            'coordinates': [obj.x, obj.y]
        }
    
    # Handle other Shapely geometries (if needed)
    elif hasattr(obj, '__geo_interface__'):
        return obj.__geo_interface__
    
    # Handle dictionaries recursively
    elif isinstance(obj, dict):
        return {key: convert_shapely_to_serializable(value) for key, value in obj.items()}
    
    # Handle lists recursively
    elif isinstance(obj, list):
        return [convert_shapely_to_serializable(item) for item in obj]
    
    # Handle tuples
    elif isinstance(obj, tuple):
        return tuple(convert_shapely_to_serializable(item) for item in obj)
    
    # Handle other types that might contain nested structures
    elif hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool, type(None))):
        # Convert custom objects to dict if they have __dict__
        return convert_shapely_to_serializable(obj.__dict__)
    
    # Return primitive types as-is
    else:
        return obj

def write_to_log_file(message, filename, query=None, jsonlines_flag=False, log_dir="log"):
    """
    Write a message to a log file in the specified directory.
    Creates the directory if it doesn't exist.

    Args:
        message: The content to write
        filename: Name of the log file
        query: Optional ID/query identifier for JSONLines
        jsonlines_flag: If True, write as JSONLines format
        log_dir: Directory to store log files
    """
    try:
        # Simplify path creation - Path.cwd() / log_dir is cleaner
        log_path = Path.cwd() / log_dir
        log_file = log_path / filename

        # Create directory (with parents if needed)
        log_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().isoformat()

        # Write to file
        if jsonlines_flag:
            # Pre-process your message before writing
            processed_message = convert_shapely_to_serializable(message)

            if query is None:
                # Provide a default if query is not specified
                query = "default_id"
            with jsonlines.open(log_file, mode='a') as writer:
                writer.write({
                    'id': query,
                    'timestamp': timestamp,
                    'code_execution_result': processed_message
                })
        else:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(' '*50 + '\n')
                f.write(f"[{timestamp}]")
                f.write(json.dumps(message))
                f.write(' '*50 + '\n')

        print(f"✅😸🐬🐶 Successfully wrote to {log_file}")

    except Exception as e:
        print(f"⚠️⚠️⚠️ Error writing to {filename}: {e}")


# Usage examples:
if __name__ == "__main__":
    # Regular text log
    write_to_log_file("This is a regular log message", "app.log")

    # JSONLines log
    write_to_log_file(
        "Code executed successfully",
        "execution.jsonl",
        query="user_query_123",
        jsonlines_flag=True
    )
