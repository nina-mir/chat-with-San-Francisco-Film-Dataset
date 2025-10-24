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
from src.map_embed_in_html import embed_in_custom_html
from src.code_executor import CodeExecutor
from src import data_loader
from src.ai_service import GenerativeAIService
from src.system_instructions import SystemInstructions
from src.logger import write_to_log_file

from pathlib import Path


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
        # Let it be True for testing! REMOVE later. Will be updated after preprocessing step
        self.need_map = True

    def _create_location_lookup(self):
        """Create a lookup dictionary: location_name -> Point geometry"""
        unique_locations = self.gdf.drop_duplicates(subset=['Locations'])
        self.location_geometry_map = dict(
            zip(unique_locations['Locations'], unique_locations['geometry'])
        )

    def _should_generate_map(self, preprocessing_result: Dict[str, Any]) -> bool:
        """
         - TO-DO this step is too rudimentary for the current state of the dev
         - it is important to deactivate this step until further upgrade [Oct 2025]
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

        print(f"\n🔥🔥🔥 QUERYPROCESSOR.process_query() CALLED! Query: '{user_query}' 🔥🔥🔥")

        results = {}

        try:
            self.user_query = user_query
            # Step 1: Preprocessing
            preprocessing_result = self.preprocess_query(user_query)
            # update need_map class variable This line and the following need attention
            # self.need_map = self._should_generate_map(preprocessing_result)

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

            # log to file the result so far
            # temporary commenting it out
            write_to_log_file(results, 'log.json', self.user_query)

            # Step 4: Execute Code
            if "code" in results:

                # Execution ...
                execution_result = self.execute_generated_code(
                    results["code"]["code"])
                # Debug statement
                print(f"✅ EXECUTION DONE: {type(execution_result)}")

                
                # 🔧🔧🔧 ADD execution result to the result object to make life easier in chatbot!🔧🔧🔧
                results["execution_result"] = execution_result
    
                print("\nExecution Result:")
                print("⚠️no printint out for now! modify it if you want to!")
                # print(execution_result)
                write_to_log_file(
                    execution_result,
                    'code_exec_results.jsonl',
                    self.user_query,
                    jsonlines_flag=True
                )

            # Step 5: Pre-Mapping Analysis (NEW)
            if self.need_map:
                print(f"🗺️ STARTING MAP ANALYSIS...")
                from src.map_analyzer import MapDataAnalyzer
                analyzer = MapDataAnalyzer(self.gdf)
                print(f"🗺️ CALLING analyzer.analyze()...")
                analysis = analyzer.analyze(execution_result.get('data'), user_query)
                print(f"✅ MAP ANALYSIS DONE")
                results["map_analysis"] = analysis
                # print(results)
                print(f"🔍 can_map={analysis['can_map']}, reason={analysis['reason']}")  # NEW

                # let's print to console some useful info for now
                print('%'*20)
                print('execution result\n\n')
                print(execution_result)
                print('^_^_'*10)
                print('\nMAP Analysis verdict:\n\n')
                print(results["map_analysis"])

                # let's write map analysis results to map_analysis_results.jsonl
                write_to_log_file(
                    results["map_analysis"],
                    'map_analysis_results.jsonl',
                    self.user_query,
                    jsonlines_flag=True
                )

                # Step 6: Generate Map (only if can_map is True)
                if analysis['can_map']:
                    print(f"🗺️ STARTING MAP GENERATION...")  # NEW

                    from src.map_generator import MapGenerator
                    
                    map_gen = MapGenerator()
                    print(f"🗺️ CALLING create_point_map()...")  # NEW

                    map_obj = map_gen.create_point_map(
                        analysis['location_data'],
                        title=execution_result["data"].get('summary', 'SF Film Locations')
                    )
                    print(f"✅ MAP GENERATED")  # NEW

                    results["map"] = map_obj
                    results["map_html"] = map_obj._repr_html_()
                    print(f"✓ Map created: {analysis['reason']}")
                    # Quick TEST --> After creating the map
                    # Save to a file
                    map_filename = f"maps/map_{int(time.time())}.html"
                    Path('maps').mkdir(exist_ok=True)  # Create Path object first
                    map_obj.save(map_filename)
                    
                    # let's try the custom HTML option too
                    embed_in_custom_html(self.user_query,execution_result, results["map_html"])

            print(f"\n🔍 QUERYPROCESSOR: About to return results")
            print(f"🔍 QUERYPROCESSOR: Final results keys: {results.keys()}")
            print(f"🔍 QUERYPROCESSOR: 'execution_result' in final results: {'execution_result' in results}")
        
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
    queries = [
        "are there any film with the word matrix in their title shot in SF? ",
        "what are all the films starring Sean Penn and all their locations in SF?",
        "what are the top 10 most frequent actors?",
        "How many movies were made in each year?",
        "which actor has appeared in a movie shot at the golden gate bridge the most times?",
        "find all movies shot within 0.5 mile radius of the Union Square. List the film names and the specific location."
    ]
    queries = ["are there any film with the word matrix in their title shot in SF? "]
    for query in queries:
        try:
            results = processor.process_query(query)
        except Exception as e:
            print(f"Error processing query: {str(e)}")
