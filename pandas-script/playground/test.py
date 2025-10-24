import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

def process_sf_film_query(gdf):
    """
    Process the film location query using the provided GeoDataFrame.

    Args:
        gdf: GeoPandas GeoDataFrame containing SF film location data

    Returns:
        dict: A standardized result dictionary with the following keys:
            - 'data': The primary result data (DataFrame, GeoDataFrame, list, etc.)
            - 'summary': A text summary of the results
            - 'metadata': Additional information about the results
    """
    try:
        # Create a copy of the dataframe to ensure we don't modify the original
        gdf_copy = gdf.copy()

        # Filter the dataframe to select rows where the 'Title' column contains the substring 'matrix'.
        films_with_matrix = gdf_copy[gdf_copy['Title'].str.lower().str.contains('matrix', na=False)]

        # Extract the 'Locations' column from the filtered dataframe.
        locations = films_with_matrix['Locations'].dropna().unique().tolist()

        # Create standardized result dictionary
        result = {
            'data': locations,
            'summary': f"Found {len(locations)} unique locations for films with 'matrix' in the title.",
            'metadata': {
                'query_type': 'attribute_filter',
            }
        }

        # Write results to log file
        with open('code_gen_result.log', 'a') as f:
            f.write('='*50 + '\n')
            f.write("Query: Find locations for films with 'matrix' in the title.\n")
            f.write('-'*50 + '\n')
            f.write(str(result['data']) + '\n')
            f.write(f"Summary: {result['summary']}\n")
            f.write('='*50 + '\n\n')

        return result

    except Exception as e:
        error_result = {
            'data': None,
            'summary': f"Error processing query: {str(e)}",
            'metadata': {
                'error': str(e),
                'error_type': type(e).__name__
            }
        }

        # Write error to log file
        with open('code_gen_result.log', 'a') as f:
            f.write('='*50 + '\n')
            f.write(f"ERROR - Query: Find locations for films with 'matrix' in the title.\n")
            f.write(f"Error: {str(e)}\n")
            f.write('='*50 + '\n\n')

        return error_result


# from code_gen_system_instructions import make_code_gen_instructions 

# preprocessing_str = 'first'
# nlp_plan_str = 'second'

# updated_content = make_code_gen_instructions(preprocessing_str, nlp_plan_str)


# print(updated_content)


# from pathlib import Path

# code_gen_system_instructions = 'code_gen_system_instructions.md'

# system_instructions = Path.cwd().joinpath("..").joinpath(code_gen_system_instructions).resolve()


# with open(system_instructions, 'r') as f:
#     content = f.read()

