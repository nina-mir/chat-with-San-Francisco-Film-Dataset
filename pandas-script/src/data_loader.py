import geopandas as gpd

#######################################################
#  Manage the loading and initial preparation of      #
#  the GeoPandas DataFrame.                           #
#######################################################

try:
    database = gpd.read_file("sf_film_May7_2025_data.gpkg")
except Exception as e:
    raise RuntimeError(f"Failed to initialize GeoDataFrame: {str(e)}")





# def _initialize_gdf(self) -> None:
        # """
        # Initialize the GeoPandas dataframe from the SQLite database.
        # Converts lat/lon columns to a geometry column with Points.
        # """
        # try:
        #     self.gdf = gpd.read_file("sf_film_May7_2025_data.gpkg")
            # # Connect to SQLite database and read the data
            # conn = sqlite3.connect(self.db_path)
            # df = pd.read_sql_query("SELECT * from sf_film_data", conn)
            # conn.close()

            # # Convert empty strings to NaN for coordinates
            # df['Lat'] = df['Lat'].replace('', np.nan)
            # df['Lon'] = df['Lon'].replace('', np.nan)

            # # Convert string columns to float
            # df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
            # df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')

            # # Create Point geometries from lat/lon
            # df['geometry'] = df.apply(
            #     lambda row: Point(row['Lon'], row['Lat'])
            #     if pd.notnull(row['Lat']) and pd.notnull(row['Lon'])
            #     else None,
            #     axis=1
            # )

            # # Convert to GeoDataFrame
            # self.gdf = gpd.GeoDataFrame(df, geometry='geometry')

            # # Set coordinate reference system (WGS84 is standard for lat/lon)
            # self.gdf.crs = "EPSG:4326"

            # # Drop the original Lat and Lon columns
            # self.gdf = self.gdf.drop(['Lat', 'Lon'], axis=1)

            # print(
            #     f"Successfully loaded GeoDataFrame with {len(self.gdf)} records")

        # except Exception as e:
        #     raise RuntimeError(f"Failed to initialize GeoDataFrame: {str(e)}")
        