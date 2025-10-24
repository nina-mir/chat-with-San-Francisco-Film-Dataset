import geopandas as gpd
from pathlib import Path

#######################################################
#  Manage the loading and initial preparation of      #
#  the GeoPandas DataFrame.                           #
#######################################################

# Create a PATH To geoPanda DB
gpdb_dir = Path('geoPandaDB')
gpdb_file = gpdb_dir / "sf_film_May7_2025_data.gpkg"

try:
    database = gpd.read_file(gpdb_file)
except Exception as e:
    raise RuntimeError(f"Failed to initialize GeoDataFrame: {str(e)}")


