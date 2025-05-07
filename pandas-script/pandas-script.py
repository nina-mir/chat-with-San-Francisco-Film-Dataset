#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Query Processor for SF Film Location Database
A class-based implementation to process natural language queries about
San Francisco film locations using GeoPandas and generative AI.
"""

import os, re
import sqlite3
import time
import json
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from typing import Dict, List, Union, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import types, Client
from google.genai.types import Part

#  system_instructions prompt utilities

from code_gen_system_instructions import make_code_gen_instructions


from dotenv import load_dotenv
###############################################
# Gemini API KEY/Basic Configuration          #
# Load environment variables from .env file   #
###############################################
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found.")
    print("Please ensure you have a .env file in the same directory")
    print("with the line: GEMINI_API_KEY='YOUR_API_KEY'")
    exit()  # Exit if the key is not found
MODEL_NAME = 'gemini-2.0-flash-001'
###############################################
#                                             #
#     PATH to SQLite database established     #
#                                             #
###############################################
DB_FILE = 'sf-films-geocode.db'

# TODO use GeoPackage Format
# To load:
# self.gdf = gpd.read_file("processed_data.gpkg")

db_path = Path.cwd().joinpath("..").joinpath(DB_FILE).resolve()
########################################################


class QueryProcessor:
    """
    A class to process natural language queries about San Francisco film locations
    using a three-step pipeline:
    1. Preprocessing: Break query into tasks and filters
    2. NLP Action Planning: Create natural language plan for execution
    3. Code Generation: Generate executable GeoPandas code
    """

    def __init__(self, api_client, db_path: str, model_name: str = MODEL_NAME):
        """
        Initialize the QueryProcessor with an API client and database path.

        Args:
            api_client: The generative AI client (e.g., Gemini)
            db_path: Path to the SQLite database with SF film data
            model_name: Name of the generative AI model to use
        """
        self.client = api_client
        self.db_path = db_path
        self.model_name = model_name
        self.gdf = None  # Will hold the GeoPandas dataframe
        self.user_query = None  # Will be updated for each query

        # System instructions for each step
        self._preprocessing_instructions = self._get_preprocessing_instructions()
        self._nlp_plan_instructions = self._get_nlp_plan_instructions()

        # Initialize the dataframe
        self._initialize_gdf()

    def _initialize_gdf(self) -> None:
        """
        Initialize the GeoPandas dataframe from the SQLite database.
        Converts lat/lon columns to a geometry column with Points.
        """
        try:
            # Connect to SQLite database and read the data
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * from sf_film_data", conn)
            conn.close()

            # Convert empty strings to NaN for coordinates
            df['Lat'] = df['Lat'].replace('', np.nan)
            df['Lon'] = df['Lon'].replace('', np.nan)

            # Convert string columns to float
            df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
            df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')

            # Create Point geometries from lat/lon
            df['geometry'] = df.apply(
                lambda row: Point(row['Lon'], row['Lat'])
                if pd.notnull(row['Lat']) and pd.notnull(row['Lon'])
                else None,
                axis=1
            )

            # Convert to GeoDataFrame
            self.gdf = gpd.GeoDataFrame(df, geometry='geometry')

            # Set coordinate reference system (WGS84 is standard for lat/lon)
            self.gdf.crs = "EPSG:4326"

            # Drop the original Lat and Lon columns
            self.gdf = self.gdf.drop(['Lat', 'Lon'], axis=1)

            print(
                f"Successfully loaded GeoDataFrame with {len(self.gdf)} records")

        except Exception as e:
            raise RuntimeError(f"Failed to initialize GeoDataFrame: {str(e)}")

    def process_query(self, user_query: str, wait_time: int = 5) -> Dict[str, Any]:
        """
        Process a natural language query through the complete pipeline.

        Args:
            user_query: The natural language query about SF film locations
            wait_time: Time to wait between API calls to avoid rate limiting

        Returns:
            Dict containing results from each step and the final code
        """
        results = {}

        try:
            self.user_query = user_query
            # Step 1: Preprocessing
            preprocessing_result = self.preprocess_query(user_query)
            results["preprocessing"] = preprocessing_result
            time.sleep(wait_time)  # Avoid rate limiting

            # Step 2: NLP Action Planning
            nlp_plan = self.generate_nlp_plan(preprocessing_result)
            results["nlp_plan"] = nlp_plan
            time.sleep(wait_time)  # Avoid rate limiting

            # Step 3: Code Generation
            code_result = self.generate_geopandas_code(
                user_query, preprocessing_result, nlp_plan
            )
            results["code"] = code_result

            return results

        except Exception as e:
            raise RuntimeError(f"Error in query processing pipeline: {str(e)}")

    def preprocess_query(self, user_query: str) -> Dict[str, Any]:
        """
        Step 1: Break the user query into tasks and filters.

        Args:
            user_query: The natural language query about SF film locations

        Returns:
            Dict containing the preprocessed tasks and filters
        """
        try:
            response = self._call_generative_api(
                self._preprocessing_instructions, user_query
            )

            # Parse the response as JSON
            if hasattr(response, 'text'):
                response_text = response.text
            else:
                response_text = str(response)

            # Ensure the response is valid JSON
            try:
                parsed_response = json.loads(response_text)
                return parsed_response
            except json.JSONDecodeError:
                # If not valid JSON, return as plain text
                return {"raw_text": response_text}

        except Exception as e:
            raise ValueError(f"Error in preprocessing step: {str(e)}")

    def generate_nlp_plan(self, preprocessing_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Step 2: Generate a natural language action plan.

        Args:
            preprocessing_result: The result from the preprocessing step

        Returns:
            Dict containing the NLP action plan
        """
        try:
            # Convert preprocessing result back to JSON string for the API call
            preprocessing_json = json.dumps(preprocessing_result)

            response = self._call_generative_api(
                self._nlp_plan_instructions, preprocessing_json
            )

            # Parse the response
            if hasattr(response, 'text'):
                response_text = response.text
            else:
                response_text = str(response)

            try:
                parsed_response = json.loads(response_text)
                return parsed_response
            except json.JSONDecodeError:
                return {"raw_text": response_text}

        except Exception as e:
            raise ValueError(f"Error in NLP plan generation step: {str(e)}")

    def generate_geopandas_code(
        self,
        user_query: str,
        preprocessing_result: Dict[str, Any],
        nlp_plan: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Step 3: Generate executable GeoPandas code.

        Args:
            user_query: The original user query
            preprocessing_result: The result from the preprocessing step
            nlp_plan: The NLP action plan

        Returns:
            Dict containing the generated code and explanation
        """
        try:
            # Create customized instructions for code generation
            code_gen_instructions = self._get_code_generation_instructions(
                preprocessing_result, nlp_plan
            )

            response = self._call_generative_api(
                code_gen_instructions, user_query)

            # Parse the response
            if hasattr(response, 'text'):
                response_text = response.text
            else:
                response_text = str(response)

            try:
                parsed_response = json.loads(response_text)
                return parsed_response
            except json.JSONDecodeError:
                # Try to extract code and explanation if not valid JSON
                return self._extract_code_from_text(response_text)

        except Exception as e:
            raise ValueError(f"Error in code generation step: {str(e)}")

    def execute_generated_code(self, code: str):
        """
        Execute the generated GeoPandas code and return both the result and its code representation.
        
        Args:
            code: The Python code to execute
                
        Returns:
            The result of executing the code
        """
        try:
            # Create a namespace with required libraries and the GeoDataFrame
            namespace = {
                "gdf": self.gdf,
                "pd": pd,
                "gpd": gpd,
                "np": np,
                "Point": Point,
                "result": None
            }

            # Add both the code and the function call to the same string
            # This ensures all functions are defined before they're called
            # NOTE: No indentation here - Python is sensitive to indentation
            full_code = f"""{code}

# Now call the main function
query_description = '{self.user_query}'
result = process_sf_film_query(gdf)
"""

            # Execute the combined code in one go
            exec(full_code, namespace)

            # Extract the result
            if 'result' in namespace:
                return namespace['result']
            else:
                return {"data": None, "summary": "Execution completed but no result was returned", "metadata": {}}

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()

            return {
                "data": None,
                "summary": f"Error executing generated code",
                "metadata": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": error_trace
                }
            }

    

    def _call_generative_api(self, system_instructions: str, user_query: str) -> Any:
        """
        Call the generative AI API with system instructions and user query.

        Args:
            system_instructions: The system instructions for the model
            user_query: The user query or input

        Returns:
            The API response
        """
        try:
            from google.genai import types

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_query,
                config=types.GenerateContentConfig(
                    system_instruction=system_instructions,
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )

            return response
        except Exception as e:
            raise RuntimeError(f"API call failed: {str(e)}")

    def _extract_code_from_text(self, text: str) -> Dict[str, str]:
        """
        Extract code and explanation from text if not properly formatted as JSON.

        Args:
            text: The raw response text

        Returns:
            Dict with code and explanation
        """
        # Simple extraction logic - improve as needed
        code_block = ""
        explanation = ""

        # Look for code blocks
        code_matches = re.findall(r'```python\n(.*?)```', text, re.DOTALL)
        if code_matches:
            code_block = code_matches[0]

        # Everything else is considered explanation
        explanation = re.sub(r'```python\n.*?```', '',
                             text, flags=re.DOTALL).strip()

        return {
            "code": code_block,
            "explanation": explanation
        }

    def _get_preprocessing_instructions(self) -> str:
        """Get the system instructions for the preprocessing step."""
        return '''
You are a helpful assistant that analyzes user queries about data manipulation using GeoPandas.

The GeoPandas dataframe where the data is stored has the following columns:
['id', 'Title', 'Year', 'Locations', 'Fun_Facts', 'Director', 'Writer','Actor_1', 'Actor_2', 'Actor_3', 'geometry']

# Your Main Job:
1. When handling queries about locations, remove any mention to "San Francisco" city, "SF", or any reference to 
        state of "California" in the query
2. Break the user query into clear, atomic tasks.
3. Identify and extract any filter conditions (e.g., "Year == 1977", "Director == Hitchcock", spatial filters like "within 1 mile of Union Square").
4. Structure filters carefully, ensuring correct use of AND/OR logic, including nested conditions when needed.
5. Ensure the output is structured precisely in the JSON format below.

# Critical Rules for DISTINCT:
- **Always** assume **distinct** values when the user asks to:
  - List films, directors, writers, or actors
  - Count films, directors, writers, or actors
- Explicitly include "list distinct" or "count distinct" as a separate task.
- Only include duplicates if the user specifically asks for all records or all locations.

# Important Logic Rules:
- Use "AND" to combine different filter categories (e.g., year filter AND location filter).
- Use "OR" when the query allows for alternatives inside the same category (e.g., films directed by X **or** acted by X).
- If needed, allow **nested logic**, like:
  {
    "logic": "OR",
    "conditions": [
      { filter1 },
      { filter2 }
    ]
  }
- Always preserve the true intent of the user's query without changing its meaning.

# Output JSON format:

{
  "tasks": [
    "First atomic task",
    "Second atomic task",
    ...
  ],
  "filters": [
    {
      "field": "field_name",
      "condition": "==, between, within_distance, contains, intersects, etc.",
      "value": "value or object",
      "type": "attribute" or "spatial"
    },
    {
      "logic": "OR" or "AND",
      "conditions": [
        { filter_object1 },
        { filter_object2 },
        ...
      ]
    },
    ...
  ],
  "filter_logic": "AND" or "OR"
}

If no filters are found, output an empty "filters" array.

# Important Style Notes:
- Be **precise**: Do not assume information not explicitly stated in the user query.
- Keep task descriptions short, clear, and action-driven.
- Distinguish between **attribute filters** (e.g., Director == "Clint Eastwood") and **spatial filters** (e.g., within 1 mile of Union Square).
- Mention distance units when using spatial filters (always use miles).
- Always describe distinct listing or counting in tasks when appropriate.
'''

    def _get_nlp_plan_instructions(self) -> str:
        """Get the system instructions for the NLP action planning step."""
        return '''
You are a GeoPandas expert tasked with converting structured query JSON into a clear,
natural language plan that explains how to execute the user's request using GeoPandas operations.

The GeoPandas dataframe where the data is stored has the following columns:
['id', 'Title', 'Year', 'Locations', 'Fun_Facts', 'Director', 'Writer','Actor_1', 'Actor_2', 'Actor_3', 'geometry']

## Input Format

You will receive a JSON structure containing:
- `tasks`: An array of atomic operations to perform
- `filters`: An array of filter conditions (may be nested)
- `filter_logic`: How the filters combine ("AND" or "OR")

## Output Requirements

Create a natural language explanation with these components:

1. **Summary Statement**: Begin with a concise one-sentence summary of what the query aims to accomplish.
   - Example: "This query finds all films made after 2000 with at least three filming locations."

2. **Data Selection Plan**: Describe the filtering process using proper GeoPandas terminology.

3. **Processing Steps**: Explain any operations performed on the filtered data.

4. **Final Output**: Describe what will be returned to the user.

## Output Format

Always structure your output as a JSON object with a single key "plan" containing a string with a numbered list of steps:

```json
{
    "plan": "To find films directed by Clint Eastwood after 2000:\\n\\n1. Load the films dataframe.\\n2. Filter rows where the Director field equals \\"Clint Eastwood\\".\\n3. Further filter to include only films with Year greater than 2000.\\n4. Return a list of distinct film titles from the filtered results."
}
```

Within the plan string:
1. Begin with the summary statement (unnumbered).
2. Number each subsequent step in the process, starting with data loading/preparation.
3. Ensure the final numbered step describes what is returned to the user.

Note that newlines in the plan string should be represented as "\\n" characters within the JSON string.
'''

    def _get_code_generation_instructions(
        self, preprocessing_result: Dict[str, Any], nlp_plan: Dict[str, str]
    ) -> str:
        """
        Get the customized system instructions for the code generation step.

        Args:
            preprocessing_result: The result from the preprocessing step
            nlp_plan: The NLP action plan

        Returns:
            Customized system instructions for code generation
        """
        # Convert inputs to strings for inclusion in the prompt
        preprocessing_str = json.dumps(preprocessing_result, indent=2)
        nlp_plan_str = json.dumps(nlp_plan, indent=2)

        return make_code_gen_instructions(preprocessing_str, nlp_plan_str)


if __name__ == "__main__":
    # Example usage
    # import os
    # from google import genai

    # # Set up API client
    # api_key = os.environ.get("GOOGLE_API_KEY")
    # if not api_key:
    #     print("Please set GOOGLE_API_KEY environment variable")
    #     exit(1)

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Database path - adjust as needed - declared at the top

    # Initialize processor
    processor = QueryProcessor(client, db_path)

    # Example query
    # query = "How many movies were made in each year?"
    query = "are there any film with the name Matrix in their title shot in SF?"

# "How many movies were made in each year?",
#              "are there any film with the name Matrix in their title shot in SF?",

    queries = ["what are some film location about 0.5 miles from Union Square?",
               "what are films made in the 70s and near Coit Tower?"
               ]
    # queries = ["are there any film with the name matrix in their title shot in SF?"]
    # queries = ["are there any films with the word matrix in their title shot in SF?"]

    # Process the queryu
    for query in queries:
        try:
            results = processor.process_query(query)
            # log to file
            with open('log.json', 'a') as f:
                f.write(json.dumps(results))

            # Print code
            if "code" in results:
                # print("Complete Results so far:")
                # print(results)

                print("Generated Code:")
                print(results["code"]["code"])

                # Execute code
                result = processor.execute_generated_code(
                    results["code"]["code"])
                print("\nExecution Result:")
                print(result)
                # print(type(result))
                # with open('code_execution_results.log', 'a') as ce:
                #     ce.write('*'*20)
                #     ce.write('\n')
                #     ce.write(query)
                #     ce.write('\n')
                #     ce.write(results["code"]["code"])
                #     ce.write('\n')
                #     ce.write(str(result))
                #     ce.write('\n')
                #     ce.write('*'*20)
                #     ce.write('\n')
                #     ce.write(str(type(result)))
                #     ce.write('\n')
                #     ce.write('*'*30)
                #     ce.write('\n'*3)

        except Exception as e:
            print(f"Error processing query: {str(e)}")

 # if "result" in local_namespace:
            #     result = local_namespace["result"]
            #     result_var_name = "result"
            # else:
            #     # If no explicit result variable, use the last variable defined
            #     all_vars = [var for var in local_namespace.keys()
            #             if not var.startswith("__") and var not in ["gdf", "pd", "gpd", "np", "Point"]]

            #     if all_vars:
            #         result_var_name = all_vars[-1]
            #         result = local_namespace[result_var_name]

            # if result is None:
            #     return None, ""

            # # Get the code representation of the result
            # if isinstance(result, gpd.GeoDataFrame):
            #     code_repr = f"{result_var_name} = gpd.GeoDataFrame(\n{result.to_string()}\n)"
            # elif isinstance(result, pd.DataFrame):
            #     code_repr = f"{result_var_name} = pd.DataFrame(\n{result.to_string()}\n)"
            # else:
            #     code_repr = f"{result_var_name} = {repr(result)}"

            # return result, code_repr


# return f'''
# ## Purpose
# You are an expert Python engineer specializing in GeoPandas with the task of translating
# natural language queries about San Francisco film locations into executable GeoPandas code. You will transform preprocessed query data and NLP action plans into precise, optimized GeoPandas commands.

# ## Input
# You will receive 1 input:
# 1. The original user query about film locations in San Francisco

# ## Given Data
# You are given the following two pieces of data
# ### 1. A preprocessing response containing identified tasks, filters, and filter logic

# {preprocessing_str}

# ### 2. An NLP action plan outlining the high-level steps to execute

# {nlp_plan_str}

# ## Expected Output
# Generate executable Python code using GeoPandas that:
# - Is syntactically correct and follows PEP 8 standards
# - Has detailed comments explaining key operations
# - Is optimized for performance
# - Includes appropriate error handling
# - Produces results in the exact format requested by the user

# Your output should be formatted as a JSON object with the following structure:
# ```json
# {{
#   "code": "# Your complete Python code here",
#   "explanation": "A brief explanation of how the code works and any assumptions made"
# }}
# ```

# ## GeoPandas DataFrame Information
# The code will operate on a GeoPandas DataFrame called `gdf` with the following structure:
# - `Title`: Name of the film (string)
# - `Year`: Year the film was released (integer)
# - `Locations`: Filming location description (string)
# - `Fun Facts`: Additional information about the location (string)
# - `Director`: Film director (string)
# - `Writer`: Film writer(s) (string)
# - `Actor_1`, `Actor_2`, `Actor_3`: Main actors (string)
# - `geometry`: GeoPandas Point geometry of the filming location (Point)

# ## Spatial Operations Reference

# When implementing spatial operations, use these GeoPandas methods appropriately:

# ### Common GeoPandas Operations:
# - `gdf.within(geometry)`: Tests if each geometry is within another geometry
# - `gdf.distance(point)`: Returns the distance between each geometry and a point
# - `gdf.buffer(distance)`: Creates a buffer of specified distance around geometries
# - `gdf.intersection(geometry)`: Returns the intersection of geometries
# - `gpd.sjoin(left_gdf, right_gdf, how='inner', op='intersects')`: Spatial join of two GeoDataFrames

# ### Location Reference Function:
# Use this helper function when a location name needs to be converted to coordinates:
# ```python
# def get_sf_landmark_point(landmark_name):
#     """Convert a San Francisco landmark name to a Point geometry"""
#     landmarks = {{
#         "Union Square": Point(-122.4074, 37.7881),
#         "Embarcadero": Point(-122.3923, 37.7956),
#         "Golden Gate Bridge": Point(-122.4786, 37.8199),
#         "Fisherman's Wharf": Point(-122.4178, 37.8080),
#         "Alcatraz Island": Point(-122.4230, 37.8270),
#         # Add other landmarks as needed
#     }}

#     # Case-insensitive landmark lookup
#     for name, point in landmarks.items():
#         if name.lower() == landmark_name.lower():
#             return point

#     # If landmark not found, attempt geocoding (assume geocoding function exists)
#     try:
#         return geocode_sf_location(landmark_name)
#     except:
#         raise ValueError(f"Could not find coordinates for location: {{landmark_name}}")
# ```

# ### Distance Calculations:
# For distance calculations, always:
# 1. Ensure geometries are in the same projection
# 2. Use the appropriate conversion factors for miles
# ```python
# # Convert distances from degrees to miles (approximate for San Francisco)
# def distance_in_miles(gdf, point):
#     # Convert to a projected CRS appropriate for the SF Bay Area
#     gdf_projected = gdf.to_crs(epsg=26910)  # NAD83 / UTM zone 10N
#     point_projected = point.to_crs(epsg=26910)

#     # Calculate distance in meters and convert to miles
#     distances = gdf_projected.distance(point_projected) * 0.000621371
#     return distances
# ```
# '''


# def execute_generated_code(self, code: str) -> Any:
    #     """
    #     Execute the generated GeoPandas code and return the result.

    #     Args:
    #         code: The Python code to execute

    #     Returns:
    #         The result of executing the code
    #     """
    #     try:
    #         # Create a local namespace with access to the GeoDataFrame
    #         local_namespace = {
    #             "gdf": self.gdf,
    #             "pd": pd,
    #             "gpd": gpd,
    #             "np": np,
    #             "Point": Point
    #         }

    #         # Execute the code in the local namespace
    #         exec(code, globals(), local_namespace)

    #         # Look for a result variable in the namespace
    #         if "result" in local_namespace:
    #             return local_namespace["result"]

    #         # If no explicit result variable, return the last variable defined
    #         all_vars = [var for var in local_namespace.keys()
    #                    if not var.startswith("__") and var not in ["gdf", "pd", "gpd", "np", "Point"]]

    #         if all_vars:
    #             return local_namespace[all_vars[-1]]

    #         return None

    #     except Exception as e:
    #         raise RuntimeError(f"Error executing generated code: {str(e)}")