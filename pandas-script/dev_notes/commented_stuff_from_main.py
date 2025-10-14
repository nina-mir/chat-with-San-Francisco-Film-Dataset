##################### hard-coded pandas statements for testing/ add more tests here ########################
############################################################################################################
                
    # gdf = processor.gdf
    # unique_films = gdf.drop_duplicates(['Title', 'Year'])
    # print("Total unique films:", len(unique_films))
    # print("Actor_1 non-empty:", (unique_films['Actor_1'].str.strip() != '').sum())
    # print("Actor_2 non-empty:", (unique_films['Actor_2'].str.strip() != '').sum()) 
    # print("Actor_3 non-empty:", (unique_films['Actor_3'].str.strip() != '').sum())

    # # Check what actual actor names exist
    # all_actors = pd.concat([unique_films['Actor_1'], unique_films['Actor_2'], unique_films['Actor_3']])
    # clean_actors = all_actors.dropna().str.strip()
    # clean_actors = clean_actors[clean_actors != '']
    # print("Sample actual actors:", clean_actors.value_counts().head(10))
    # exit(1)
    

# Example query
# query = "How many movies were made in each year?"
# query = "are there any film with the name Matrix in their title shot in SF?"

# # "How many movies were made in each year?",
# #              "are there any film with the name Matrix in their title shot in SF?",

#     queries = [
#         "what are some film location about 0.5 miles from Union Square?",
#         "what are films made in the 70s and near Coit Tower?"
#     ]

############################################################################################################

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

# def _call_generative_api(self, system_instructions: str, user_query: str) -> Any:
#         """
#         Call the generative AI API with system instructions and user query.

#         Args:
#             system_instructions: The system instructions for the model
#             user_query: The user query or input

#         Returns:
#             The API response
#         """
#         try:
#             from google.genai import types

#             response = self.client.models.generate_content(
#                 model=self.model_name,
#                 contents=user_query,
#                 config=types.GenerateContentConfig(
#                     system_instruction=system_instructions,
#                     response_mime_type="application/json",
#                     temperature=0.2,
#                 ),
#             )

#             return response
#         except Exception as e:
#             raise RuntimeError(f"API call failed: {str(e)}")


# def _get_preprocessing_instructions(self) -> str:
#         """Get the system instructions for the preprocessing step."""
#         return '''
# You are a helpful assistant that analyzes user queries about data manipulation using GeoPandas.

# # STEP 1: Data Modification Check
# Your first task is to determine if the query is attempting to modify the database in any way.

# A modification query would include clear intent to:
# - Add new data (e.g., "Add this film to the database")
# - Update existing data (e.g., "Change the Year for The Godfather to 1972")
# - Delete data (e.g., "Remove all films from 1999")
# - Save or export modified data (e.g., "Save these changes")

# Examples of modification queries:
# - "Insert a new film called 'Star Wars'"
# - "Update the location for Vertigo"
# - "Delete films directed by Spielberg"
# - "Add a new entry with id=500"

# Examples of read-only queries (NOT modification):
# - "Show me films with 'matrix' in the title"
# - "List films shot in Union Square"
# - "Count films directed by Hitchcock"
# - "Find locations that appear in multiple films"
# - "Add locations to my search results" (this is about viewing, not modifying)

# If you detect a data modification request, immediately respond with this JSON:
# {
#   "error": true,
#   "message": "This operation cannot be performed as it would modify the database. Only read-only operations are permitted.",
#   "requested_operation": "DESCRIBE_OPERATION_HERE"
# }

# # STEP 2: Read-Only Query Processing
# If the query is read-only, proceed with these instructions:

# The GeoPandas dataframe has the following columns:
# ['id', 'Title', 'Year', 'Locations', 'Fun_Facts', 'Director', 'Writer','Actor_1', 'Actor_2', 'Actor_3', 'geometry']

# Your job for valid read-only queries:
# 1. When handling queries about locations, remove any mention to "San Francisco" city, "SF", or any reference to
#         state of "California" in the query
# 2. Break the user query into clear, atomic tasks.
# 3. Identify and extract any filter conditions (e.g., "Year == 1977", "Director == Hitchcock", spatial filters like "within 1 mile of Union Square").
# 4. Structure filters carefully, ensuring correct use of AND/OR logic, including nested conditions when needed.
# 5. Ensure the output is structured precisely in the JSON format below.

# # Critical Rules for DISTINCT:
# - **Always** assume **distinct** values when the user asks to:
#   - List films, directors, writers, or actors
#   - Count films, directors, writers, or actors
# - Explicitly include "list distinct" or "count distinct" as a separate task.
# - Only include duplicates if the user specifically asks for all records or all locations.

# # Important Logic Rules:
# - Use "AND" to combine different filter categories (e.g., year filter AND location filter).
# - Use "OR" when the query allows for alternatives inside the same category (e.g., films directed by X **or** acted by X).
# - If needed, allow **nested logic**.
# - Always preserve the true intent of the user's query without changing its meaning.

# # Output JSON format for valid read-only queries:

# {
#   "tasks": [
#     "First atomic task",
#     "Second atomic task",
#     ...
#   ],
#   "filters": [
#     {
#       "field": "field_name",
#       "condition": "==, between, within_distance, contains, intersects, etc.",
#       "value": "value or object",
#       "type": "attribute" or "spatial"
#     },
#     {
#       "logic": "OR" or "AND",
#       "conditions": [
#         { filter_object1 },
#         { filter_object2 },
#         ...
#       ]
#     },
#     ...
#   ],
#   "filter_logic": "AND" or "OR"
# }

# If no filters are found, output an empty "filters" array.
# '''


# def _get_nlp_plan_instructions(self) -> str:
#         """Get the system instructions for the NLP action planning step."""

#         return '''
# You are a GeoPandas expert tasked with converting structured query JSON into a clear,
# natural language plan that explains how to execute the user's request using GeoPandas operations.

# The GeoPandas dataframe where the data is stored has the following columns:
# ['id', 'Title', 'Year', 'Locations', 'Fun_Facts', 'Director', 'Writer','Actor_1', 'Actor_2', 'Actor_3', 'geometry']

# ## Input Format

# You will receive a JSON structure containing:
# - `tasks`: An array of atomic operations to perform
# - `filters`: An array of filter conditions (may be nested)
# - `filter_logic`: How the filters combine ("AND" or "OR")

# ## Output Requirements

# Create a natural language explanation with these components:

# 1. **Summary Statement**: Begin with a concise one-sentence summary of what the query aims to accomplish.
#    - Example: "This query finds all films made after 2000 with at least three filming locations."

# 2. **Data Selection Plan**: Describe the filtering process using proper GeoPandas terminology.

# 3. **Processing Steps**: Explain any operations performed on the filtered data.

# 4. **Final Output**: Describe what will be returned to the user.

# ## Output Format

# Always structure your output as a JSON object with a single key "plan" containing a string with a numbered list of steps:

# ```json
# {
#     "plan": "To find films directed by Clint Eastwood after 2000:\\n\\n1. Load the films dataframe.\\n2. Filter rows where the Director field equals \\"Clint Eastwood\\".\\n3. Further filter to include only films with Year greater than 2000.\\n4. Return a list of distinct film titles from the filtered results."
# }
# ```

# Within the plan string:
# 1. Begin with the summary statement (unnumbered).
# 2. Number each subsequent step in the process, starting with data loading/preparation.
# 3. Ensure the final numbered step describes what is returned to the user.

# Note that newlines in the plan string should be represented as "\\n" characters within the JSON string.
# '''

    # def _get_code_generation_instructions(
    #     self, preprocessing_result: Dict[str, Any], nlp_plan: Dict[str, str]
    # ) -> str:
    #     """
    #     Get the customized system instructions for the code generation step.

    #     Args:
    #         preprocessing_result: The result from the preprocessing step
    #         nlp_plan: The NLP action plan

    #     Returns:
    #         Customized system instructions for code generation
    #     """
    #     # Convert inputs to strings for inclusion in the prompt
    #     preprocessing_str = json.dumps(preprocessing_result, indent=2)
    #     nlp_plan_str = json.dumps(nlp_plan, indent=2)

    #     return make_code_gen_instructions(preprocessing_str, nlp_plan_str)


#         try:
#             # Create a namespace with required libraries and the GeoDataFrame
#             namespace = {
#                 "gdf": self.gdf,
#                 "pd": pd,
#                 "gpd": gpd,
#                 "np": np,
#                 "Point": Point,
#                 "result": None
#             }

#             # Add both the code and the function call to the same string
#             # This ensures all functions are defined before they're called
#             # NOTE: No indentation here - Python is sensitive to indentation
#             full_code = f"""{code}

# # Now call the main function
# result = process_sf_film_query(gdf)
# """

#             # Execute the combined code in one go
#             exec(full_code, namespace)

#             # Extract the result
#             if 'result' in namespace:
#                 return namespace['result']
#             else:
#                 return {"data": None, "summary": "Execution completed but no result was returned", "metadata": {}}

#         except Exception as e:
#             import traceback
#             error_trace = traceback.format_exc()

#             return {
#                 "data": None,
#                 "summary": f"Error executing generated code",
#                 "metadata": {
#                     "error": str(e),
#                     "error_type": type(e).__name__,
#                     "traceback": error_trace
#                 }
#             }
