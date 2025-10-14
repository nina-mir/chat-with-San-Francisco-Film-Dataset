"""
Query Processor for SF Film Location Database
A class-based implementation to process natural language queries about
San Francisco film locations using GeoPandas and generative AI.
"""

import re
import time
import json
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from typing import Dict, Any

#  import API keys/Model setting/Databse file
from src.code_executor import CodeExecutor
from src import data_loader
from src.ai_service import GenerativeAIService
from src.system_instructions import SystemInstructions

# to write to a JSON file in a continuous/beautiful manner
import jsonlines


class QueryProcessor:
    """
    A class to process natural language queries about San Francisco film locations
    using a three-step pipeline:
    1. Preprocessing: Break query into tasks and filters
    2. NLP Action Planning: Create natural language plan for execution
    3. Code Generation: Generate executable GeoPandas code
    """

    def __init__(self):
        """
        Initialize the QueryProcessor with an API client and database path.

        Args:
            api_client: The generative AI client (e.g., Gemini)
            db_path: Path to the SQLite database with SF film data
            model_name: Name of the generative AI model to use
        """
        self.ai_service = GenerativeAIService()
        self.gdf = data_loader.database  # Holds the GeoPandas dataframe
        self.user_query = None  # Will be updated for each query
        self.code_executor = CodeExecutor(self.gdf)

        # System instructions for each step
        self.system_instructions = SystemInstructions()
        self._preprocessing_instructions = self.system_instructions.get_preprocessing_instructions()
        self._nlp_plan_instructions = self.system_instructions.get_nlp_plan_instructions()

        # Create location-to-geometry lookup
        self._create_location_lookup()
        # Map flag
        self.need_map = None  # Will be updated after preprocessing step

    def _create_location_lookup(self):
        """Create a lookup dictionary: location_name -> Point geometry"""
        unique_locations = self.gdf.drop_duplicates(subset=['Locations'])
        self.location_geometry_map = dict(
            zip(unique_locations['Locations'], unique_locations['geometry'])
        )

    def _should_generate_map(self, preprocessing_result: Dict[str, Any]) -> bool:
        """
        Determine if map generation is needed based on preprocessing results.

        Args:
            preprocessing_result: The result from the preprocessing step

        Returns:
            bool: True if map generation is needed, False otherwise
        """
        filters = preprocessing_result.get('filters', [])

        for filter_item in filters:
            if (filter_item.get('field') == 'geometry' or
                    filter_item.get('type') == 'spatial'):
                return True

        return False

    def execute_generated_code(self, code: str):
        """
        Execute the generated GeoPandas code and return both the result and its code representation.

        Args:
            code: The Python code to execute

        Returns:
            The result of executing the code
        """

        return self.code_executor.execute_with_validation(code)

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

    def check_preprocessing_error(self, preprocessing_result):
        """
        Check if the preprocessing result contains an error and exit if it does.

        Args:
            preprocessing_result (dict): The result from the preprocessing step

        Returns:
            None: The function will exit the program if an error is detected
        """
        # Check if the result has an 'error' key with a value of True
        if preprocessing_result.get('error') == True:
            # Print the error message if available
            if 'message' in preprocessing_result:
                print(f"ERROR: {preprocessing_result['message']}")

            # Print the requested operation if available
            if 'requested_operation' in preprocessing_result:
                print(
                    f"Requested operation: {preprocessing_result['requested_operation']}")

            print("Exiting due to data modification request.")
            # Exit the program
            import sys
            sys.exit(1)

        # If no error is found, the function returns nothing and execution continues

    def preprocess_query(self, user_query: str) -> Dict[str, Any]:
        """
        Step 1: Break the user query into tasks and filters.

        Args:
            user_query: The natural language query about SF film locations

        Returns:
            Dict containing the preprocessed tasks and filters
        """
        try:

            response = self.ai_service.generate_content(
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

            response = self.ai_service.generate_content(
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
            code_gen_instructions = self.system_instructions.get_code_generation_instructions(
                preprocessing_result, nlp_plan
            )

            response = self.ai_service.generate_content(
                code_gen_instructions, user_query
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
                # Try to extract code and explanation if not valid JSON
                return self._extract_code_from_text(response_text)

        except Exception as e:
            raise ValueError(f"Error in code generation step: {str(e)}")

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
            # update need_map class variable
            self.need_map = self._should_generate_map(preprocessing_result)

            results["preprocessing"] = preprocessing_result
            self.check_preprocessing_error(preprocessing_result)
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


if __name__ == "__main__":
    # Initialize processor
    processor = QueryProcessor()

    queries = [
        "are there any film with the word matrix in their title shot in SF? "]
    queries = ["How many movies were made in each year?"]
    queries = ["what are the top 10 most frequent actors?"]
    # queries = ["what are the top 10 most frequent locations used? Could you also include the name of films for each location?"]
    # queries = ["what are all the location within 0.5 mile radius of Union Square?"]
    # queries = ["what are all the location within 0.2 mile radius of Embarcadero?"]
    # queries = ["what are the films made from 1900 to 1930? Please giv me all the infor for each film!"]
    # queries = ["what is the number of unique locations in the database?"]
    # queries = ["Provide me with info about the number of rows in the database?"]

    # queries = ["which direcotr made the most films in SF? List their films too!"]
    # queries = [
    #     "list all films with each one's complete dataset that has the word matrix in their title."]

    # queries = [
    #     "are there any film with an actor, writer or director called Chaplin "]
    queries = [
        "are there any film with the word matrix in their title shot in SF? ",
        "what are all the films starring Sean Penn and all their locations in SF?",
        "what are the top 10 most frequent actors?",
        "How many movies were made in each year?",
        "which actor has appeared in a movie shot at the golden gate bridge the most times?"
    ]

    queries = ["what are the top 10 most frequent locations?"]
    queries = ["find all movies shot within 0.5 mile radius of the Union Square. List the film names and the specific location."]
    # queries = [ "which actor has appeared in a movie shot at the golden gate bridge the most times?"]
    # queries = ["what year had the most number of unique films shot in SF?"]
    # queries = [ "how many unique actors have appeared in the 6 least popular filming locations?"]
    #queries = [ "weighted by number of films at each location, what is the average latitude and longitude of all movies in the database?"]
    # queries = [ "we assign a score 'x' to a film based on the following attributes: 100 points for a movie shot at the center of SF at 37.7749° N, 122.4194° W, falling off by 10 points per 100 yards. if a movie was shot in multiple places in SF, use the place closest to the center. Add 100 points for a movie made in 2025, falling off by 5 points per year (ie. 95 points for a movie made in 2024). what are x for the top 5 movies and bottom 5 movies? do this all in memory, do not modify the database."]


    # Process the queryu
    for query in queries:
        try:
            results = processor.process_query(query)
            print(f"need map situation is: {processor.need_map}")
            # log to file
            with open('log.json', 'a') as f:
                f.write(' '*50 + '\n')
                f.write(json.dumps(results))
                f.write(' '*50 + '\n')

            # Print code
            if "code" in results:
                # print("Complete Results so far:")
                # print(results)

                print("Generated Code:")
                print(results["code"]["code"])

                # Execute code
                execution_result = processor.execute_generated_code(
                    results["code"]["code"])
                print("\nExecution Result:")
                print(execution_result)
                with jsonlines.open('code_exec_results.jsonl', mode='a') as writer:
                    writer.write(
                        {'id': query, 'code_execution_result': execution_result})
                    # f.write(' '*50 + '\n')
                    # f.write(json.dumps(results))

                # needs_map = processor.need_map
                # locations_found = processor._extract_locations_from_results(execution_result)

                # if needs_map and locations_found:
                #     map_result = processor._create_location_map(locations_found)
                print(f"need map situation is: {processor.need_map}")

        except Exception as e:
            print(f"Error processing query: {str(e)}")
