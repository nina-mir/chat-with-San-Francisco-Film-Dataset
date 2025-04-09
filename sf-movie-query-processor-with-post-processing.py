###############################################
# LIBRARY IMPORTS
###############################################
import os
from dotenv import load_dotenv
# import glob
import sqlite3
from google import genai
from google.genai import types, Client
import pandas as pd
import json
import dataclasses
import typing_extensions as typing
import pathlib
import textwrap
import pprint
import re
# from IPython.display import HTML, Markdown, display

###############################################
# Pandas setting
###############################################
pd.set_option('display.max_rows', 200)

###############################################
# Gemini API KEY/Basic Configuration
# Load environment variables from .env file
###############################################
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
model_name = 'gemini-2.0-flash'
# Only run this block for Gemini Developer API
# Configure Gemini
client = genai.Client(api_key=GEMINI_API_KEY)
# The client.models modules exposes model inferencing and model getters.
# models = client.models
###############################################
# PATH to SQLite database
###############################################
DB_FILE = 'sf-films-geocode.db'
###############################################
# UTILITY FUNCTIONS
###############################################


def call_generative_api(system_instructions: str, user_query: str):
    """
    Generate a response using the specified model and user query.
    Args:
        system_instructions (str): The system instructions for the model.
        user_query (str): The user query for which to generate a response.
    Returns:
        str: The generated response text.
    """
    response = client.models.generate_content(
        model=model_name,
        contents=user_query,
        config=types.GenerateContentConfig(
            system_instruction=system_instructions,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

    return response


def extract_code_blocks(llm_response: str):
    """Extracts multiple code blocks from the LLM response."""
    code_blocks = re.findall(r"#begin(.*?)#end", llm_response, re.DOTALL)
    if not code_blocks:
        # Fallback to a more lenient extraction method if no code blocks are found
        code_blocks = re.findall(r"```python(.*?)```", llm_response, re.DOTALL)
        if not code_blocks:
            raise ValueError("No valid code blocks found in the LLM response.")
    return [block.strip() for block in code_blocks]

# test
# response = call_generative_api(
#     client, model_name, prompt, "What are some movies shot in Coit Tower?")
# print(response)

###############################################
#
# MAIN CLASS DEFINITION
# POST-PROCESSING ADDITION
#
###############################################

class SFMovieQueryProcessor:
    """
    A class representing the processing step of the user query
    in a SQLite query or a Pandas dataframe with post-processing capabilities
    """

    def __init__(self, db_file: str, user_query: str):
        self.db_file = db_file
        self.user_query = user_query
        self.db_structure = self._get_db_structure()
        self.sample_data = self._get_sample_data()
        # Store the last query results for potential follow-up questions
        self.last_full_results = None
        # self.output_folder = self.create_output_folder()
        # os.makedirs(self.output_folder, exist_ok=True)

    # [existing methods remain the same]
    
    def _get_db_connection(self):
        """
        Create a new database connection

        Returns:
            tuple: (connection, cursor)
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        return conn, cursor

    def _get_db_structure(self) -> dict:
        """Retrieves the structure of the SQLite database."""
        conn, cursor = self._get_db_connection()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        structure = {}
        table_name = tables[0][0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        structure[table_name] = [col[1] for col in columns]
        conn.close()
        return structure

    def _get_sample_data(self, sample_size: int = 5) -> dict:
        """
        Retrieves a sample of data (up to sample_size rows) from each table
        in the given SQLite database file as a list of dictionaries.

        Args:
            db_file (str): The path to the SQLite database file.
            sample_size (int, optional): The maximum number of sample rows to retrieve
                                            from each table. Defaults to 5.

        Returns:
            dict: A dictionary where keys are table names and values are lists of
                    dictionaries, with each dictionary representing a row.
                    Returns an empty dictionary if the database file is not found or an error occurs.
        """
        sample_data = {}
        try:
            conn, cursor = self._get_db_connection()

            structure = self._get_db_structure()
            for table_name, columns in structure.items():
                cursor.execute(
                    f"SELECT * FROM {table_name} LIMIT {sample_size}")
                rows = cursor.fetchall()
                sample_data[table_name] = [
                    dict(zip(columns, row)) for row in rows]

        except sqlite3.Error as e:
            print(f"# SQLite error: {e}")
        except FileNotFoundError:
            print(f"# Error: Database file '{self.db_file}' not found.")
        finally:
            if conn:
                conn.close()
        return sample_data

    def preprocess_query(self, raw_query: str) -> str:
        """
        Basic preprocessing of the user's query.
        Args:
            raw_query (str): The raw user query.
        Returns:
            str: The preprocessed query.
        """
        # Convert to lowercase
        cleaned_query = raw_query.lower()

        # Remove "in san francisco" as the data is specific to SF
        cleaned_query = cleaned_query.replace(
            "in san francisco", "").strip()
        
        cleaned_query = cleaned_query.replace(
            "in sf", "").strip()

        print(f"# Raw query: {raw_query}")
        print(f"# Preprocessed query: {cleaned_query}")
        return cleaned_query

    def initial_query_prompt_maker(self, complexity: str) -> str:
        """
        Creates a structured prompt for generating optimized SQLite queries based on user questions
        and previously determined complexity level. Modified to retrieve full records.
        """

        initial_query_prompt = f"""
        # SQLite Query Generator for San Francisco Film Database

        ## User Request
        Generate a SQLite query to retrieve COMPLETE RECORDS that answer the user_input.

        ## Query Parameters
        - Complexity Level: {complexity}
        - Query Type: {'Simple direct lookup' if complexity == 'SIMPLE_SQLITE' else 'Complex multi-condition or aggregation'}
        - Search Type: Case-insensitive
        - Result Type: FULL RECORDS (always select * from the table)

        ## Database Context

        ### Database Structure
        {json.dumps(self.db_structure, indent=2)}

        ### Sample Data from sf_film_data table
        {json.dumps(self.sample_data, indent=2)}

        ## Technical Requirements

        You are a world-class SQLite expert. Your task is to create a precise, efficient, and properly optimized query that:

        1. **Always Retrieves Complete Records**:
        - ALWAYS use SELECT * to retrieve all columns from each matching record
        - This is critically important as we'll post-process the results to extract specific information

        2. **Matches Complexity Level**: 
        - {'Use simple WHERE clauses and avoid unnecessary JOINs or subqueries' if complexity == 'SIMPLE_SQLITE' else 'Utilize appropriate JOINs, subqueries, aggregations, or multiple conditions as needed'}

        3. **Ensures Accuracy**:
        - Validate column names against the schema
        - Handle potential NULL values appropriately
        - Use proper data type handling (TEXT, INTEGER, etc.)

        4. **Implements Case-Insensitive Search**:
        - Use LOWER() or UPPER() functions for text comparisons
        - Example: WHERE LOWER(column_name) LIKE LOWER('%search_term%')
        - Apply case-insensitive search to all text-based filtering conditions
        - Ensure case-insensitivity doesn't adversely impact query performance

        5. **Handles Distinct/Unique Data Appropriately**:
        - Use DISTINCT only when absolutely necessary to avoid duplicates
        - For aggregations, ensure proper handling of distinct/non-distinct as needed
        - Remember: We generally want full records, so use DISTINCT cautiously

        6. **Follows Best Practices**:
        - Use descriptive aliases for readability
        - Properly quote string literals
        - Use parameterized queries when appropriate
        - Follow SQLite syntax conventions precisely

        7. **Optimizes Performance**:
        - Use appropriate indexing hints if needed
        - Avoid full table scans when possible
        - Structure WHERE clauses for efficiency

        8. **Clarifies Intent**:
        - Include explanatory comments above complex logic
        - Note any assumptions made about the data
        - Explain any special handling or edge cases

        ## Response Format

        Respond with a JSON object in the following format:
        {{
        "query": "..."
        }}

        Provide only the final, executable SQLite query code:

        -- Your optimized SQLite query here with comments
        -- REMEMBER: Always use SELECT * to retrieve complete records
        -- Ensure all text searches are case-insensitive
        """
        return initial_query_prompt

    # [Other existing methods remain the same]
    
    def intent_complexity_prompt_maker(self) -> str:
        """
        Creates a structured prompt for an LLM to analyze user queries against a San Francisco
        film database and determine both the intent and required complexity level.

        :return: A formatted prompt string for the LLM with database structure, examples, and instructions.
        """

        prompt_template = f'''
        # San Francisco Film Query Analyzer

        ## Database Context
        Analyze the user query in the context of a database table named 'sf_film_data' with the following
        structure and sample data:

        ### Database Structure
        {json.dumps(self.db_structure, indent=2)}

        ### Sample Data from sf_film_data table
        {json.dumps(self.sample_data, indent=2)}

        ## Task Description
        Based on the query, identify the user's intention and the complexity required to answer it.

        ### Complexity Levels
        - **SIMPLE_SQLITE**: Direct queries with simple conditions
        - **COMPLEX_SQLITE**: Queries requiring joins, aggregations, or multiple conditions
        - **PYTHON_PANDAS**: Queries needing data manipulation beyond SQL capabilities
        - **PYTHON_VISUALIZATION**: Queries requiring visual representation of data

        ## Analysis Framework

        ### Column-Based Intent Recognition
        **Consider the column names and the type of data present in the sample rows when determining the intent and complexity.**

        #### Location-Based Queries
        - If the query mentions a location and the 'Locations' column contains text descriptions of filming spots,
        then the intent is most likely related to finding movies/TV shows by location
        - **SIMPLE_SQLITE**: Direct location match (e.g., "Shows filmed at Golden Gate Bridge")
        - **COMPLEX_SQLITE**: Multiple locations or nuanced search

        #### Actor-Based Queries
        - If the query is about an actor, check the 'Actor-1', 'Actor-2', 'Actor-3' columns
        - **SIMPLE_SQLITE**: Direct match for one actor
        - **COMPLEX_SQLITE**: Involves more than one actor or nuanced search

        #### Production Staff Queries
        - If the query is about a writer or director, check the 'Director' and 'Writer' columns
        - **SIMPLE_SQLITE**: Direct match for one person
        - **COMPLEX_SQLITE**: Involves multiple people or nuanced search

        #### Trivia and Facts Queries
        - If the query is about interesting things about a location, check the 'Fun_Facts' column
        - **SIMPLE_SQLITE**: Direct match for facts
        - **COMPLEX_SQLITE**: Nuanced search for facts

        #### Geospatial Queries
        - If the query involves distance or location analysis, use the 'Lat' and 'Lon' columns
        - **PYTHON_PANDAS**: Calculations involving distances
        - **PYTHON_VISUALIZATION**: Creating maps or visual representations

        ### Classification Rules
        - A query requiring a simple WHERE clause on a single column is likely **SIMPLE_SQLITE**
        - Queries involving joins, aggregations (like COUNT, AVG), or multiple conditions with AND/OR might be **COMPLEX_SQLITE**
        - If the query asks for analysis involving grouping, pivoting, or calculations across multiple rows, classify it as **PYTHON_PANDAS**
        - If the query explicitly requests a visual representation of the data (chart, graph, map), classify it as **PYTHON_VISUALIZATION**

        ## Example Classifications

        ### SIMPLE_SQLITE Examples
        - Query: "What are some movies shot in Coit Tower?" → Intent: Find movies by location
        - Query: "What are some movies by Clint Eastwood?" → Intent: Find movies by an actor
        - Query: "List all films that mention 'Golden Gate Bridge' in their Locations." → Intent: Find movies by keyword in location
        - Query: "What are all the movies shot in Coit Tower or Embarcadero from 1910 to 2020?" → Intent: Find movies by location and time range
        - Query: "What is the oldest movie shot in San Francisco and its locations?" → Intent: Find a movie by time range and location

        ### COMPLEX_SQLITE Examples
        - Query: "What are some films made in SF in the 80s made by Spielberg?" → Intent: Find movies by director and year range
        - Query: "What are some films made in SF by either Spielberg or Eastwood?" → Intent: Find movies by directors


        ### PYTHON_PANDAS Examples
        - Query: "What years had the most movies filmed?" → Intent: Analyze movie counts by year

        ### PYTHON_VISUALIZATION Examples
        - Query: "Show the distribution of filming locations on a map." → Intent: Visualize movie locations

        ### Unable to Determine (IDK) Examples
        - Query: "What is the weather in London?" → Reason: Mentions locations outside of San Francisco
        - Query: "Who won the last presidential election?" → Reason: Unrelated to movies or filming
        - Query: "What are the ingredients for a chocolate cake?" → Reason: Unrelated to movies or filming
        - Query: "What is the population of New York City?" → Reason: Unrelated to movies or filming
        - Query: "Explain the theory of relativity." → Reason: Unrelated to movies or filming
        - Query: "What is the capital of France?" → Reason: Unrelated to movies or filming
        - Query: "Tell me something interesting." → Reason: Intent fundamentally unclear even with context
        - Query: "What is the meaning of life?" → Reason: Intent fundamentally unclear even with context
        - Query: "Find movies." → Reason: Intent fundamentally unclear even with context
        - Query: "What happened?" → Reason: Intent fundamentally unclear even with context
        - Query: "Search everything." → Reason: Intent fundamentally unclear even with context
        - Query: "List all sci-fi movies with warp drive." → Reason: Information not present in database
        - Query: "Find movies with a Rotten Tomatoes score above 90%." → Reason: Information not present in database
        - Query: "What are some Bollywood films shot in San Francisco?" → Reason: Information not present in database

        ## Response Format
        Respond with a JSON object in the following format:
        {{
        "intent": "...",
        "complexity": "..."
        }}

        If you cannot determine the intent or complexity, respond with:
        {{
        "intent": "IDK",
        "complexity": "IDK",
        "reason": "..."
        }}
        '''
        return prompt_template

    def assess_query_complexity(self, user_query: str):
        """Assesses the complexity of the user's query."""
        print('assess_query_says_hi')
        response = call_generative_api(
            self.intent_complexity_prompt_maker(), user_query)
        if not response:
            return {'intent': "Failed to assess query complexity. Defaulting to Python with pandas.",
                    'complexity': "PYTHON_PANDAS"}
        return json.loads(response.text)

    def feedback_prompt_maker(self, user_query: str) -> str:
        """
        Creates a structured prompt for obtaining expert feedback on a generated SQLite query.
        Modified to emphasize retrieving full records.
        """

        feedback_prompt = f"""
    # SQLite Query Review: Expert Feedback

    ## Context
    - User Query: "{user_query}"
    - a database table named 'sf_film_data' is where all the queries will be used on
    - Generated SQLite Query will be given to you. 
    ```

    ## Reviewer Role
    You are a senior database engineer specializing in SQLite optimization. Your task is to provide actionable feedback on the query above. Be thorough but prioritize feedback that would significantly improve the query.

    ## Evaluation Criteria

    1. **Completeness of Record Retrieval**
    - MOST IMPORTANT: Does the query use SELECT * to retrieve all columns for post-processing?
    - If not, this is a critical issue that must be fixed in the revised query

    2. **Correctness & Accuracy**
    - Does the sqlite query correctly address the user's question?
    - Are there logical errors or misinterpretations?
    - Will it return the expected data?

    3. **Performance Optimization**
    - Are there inefficient patterns (unnecessary scans, poor join order)?
    - Could indexes be better utilized?
    - Is the query unnecessarily complex for the task?

    4. **SQLite-Specific Considerations**
    - Does the query use SQLite dialect appropriately?
    - Are there SQLite-specific optimizations that could be applied?
    - Does it handle SQLite's type affinity system correctly?
    - Does it understand that SQLite requires LOWER() for case-insensitive searches?

    5. **Robustness & Safety**
    - How does it handle NULL values, empty results, or edge cases?
    - Is text searching properly case-insensitive?
    - Are there potential injection risks?

    6. **Readability & Maintainability**
    - Is the query well-formatted and easy to understand?
    - Are there helpful comments explaining complex logic?
    - Could variable naming or structure be improved?

    ## Response Format
    Provide your assessment in the following format:

    1. **Overall Assessment**: Brief summary evaluation (1-2 sentences)
    2. **Key Strengths**: List 2-3 specific positive aspects
    3. **Primary Improvements Needed**: List specific issues in order of importance
    4. **Optimized Query**: If substantial changes are needed, provide an improved version
    5. **Explanation**: Brief explanation of major changes (if optimized query provided)

    Be direct and specific in your feedback. If the query is already well-optimized, acknowledge this rather than finding minor issues.
    """

        return feedback_prompt

    def improved_query_prompt_maker(self, feedback: str) -> str:
        """
        Creates a structured prompt for revising an SQLite query based on expert feedback.
        Modified to emphasize retrieving full records.
        """
        
        improved_query_prompt = f"""
        # SQLite Query Optimization Task

        ## Background
        You are a world-class SQLite query optimization expert. 
        Your task is to revise and improve a query based on expert feedback.

        ## Source Materials

        ### Initial Query to be provided. 
        

        ### Expert Feedback Assessment
        {feedback} 

        ## Task Requirements
        1. MOST CRITICAL: ENSURE THE QUERY USES "SELECT *" TO RETRIEVE FULL RECORDS
        2. Keep in mind that SQLite requires LOWER() for case-insensitive searches 
        3. Apply all critical improvements mentioned in the feedback
        4. Maintain or enhance the query's core functionality
        5. Ensure the revised query is:
        - Properly optimized for performance
        - Case-insensitive for text searches
        - Robust against edge cases
        - Well-formatted and readable
        - Free of syntax errors
        - Compatible with SQLite dialect

        ## Important Guidelines
        - Make decisive improvements rather than minimal changes
        - Include helpful comments explaining complex logic or significant changes
        - Do not introduce new functionality beyond the scope of the original query
        - Ensure all text comparisons remain case-insensitive
        - ALWAYS USE "SELECT *" TO RETRIEVE FULL RECORDS - THIS IS NON-NEGOTIABLE

        ## Response Format
        Respond with a JSON object with one field:
        {{
        "revised-query": " Your optimized SQLite query here. "
        }}

        """
            
        return improved_query_prompt

    def post_processing_prompt_maker(self, user_query: str, full_results_sample) -> str:
        """
        Creates a prompt for post-processing the full record results into a concise answer.
        
        Args:
            user_query: The original user query
            full_results_sample: A sample of the full results (first few rows or all if small)
            
        Returns:
            str: A prompt for the LLM to extract the relevant information
        """
        post_processing_prompt = f"""
        # Post-Processing for San Francisco Film Database Query Results
        
        ## User Query
        "{user_query}"
        
        ## Full Results Retrieved
        {full_results_sample.to_json(orient='records')}
        
        ## Task Description
        You are an expert in information extraction and summarization. Your task is to:
        
        1. Extract the most relevant information from the full results to directly answer the user's query
        2. Format the answer in a concise, readable way
        3. Include only the information requested by the user
        4. Organize the information logically (e.g., chronologically for dates, alphabetically for names if appropriate)
        5. Present the information in a conversational, helpful tone
        
        ## Response Format
        Respond with a JSON object containing two fields:
        
        ```json
        {{
            "concise_answer": "A direct, concise answer formatted for readability that addresses the user's specific query",
            "additional_info_available": "A brief description of what additional information is available from the full records if the user wants to know more"
        }}
        ```
        
        The concise_answer should be formatted for easy reading (using appropriate line breaks, bullet points if needed, etc.)
        The additional_info_available should briefly mention what other information you could share about these results.
        """
        return post_processing_prompt

    def generate_initial_query(self, user_query, complexity):
        """Generate the initial SQLite query based on user input and complexity"""

        print('# Generating initial query')
        initial_step_instructions = self.initial_query_prompt_maker(complexity)
        initial_query = call_generative_api(initial_step_instructions, user_query)

        if not initial_query:
            return None

        query = json.loads(initial_query.text).get('query', 'no query generated!')
        return query if query != 'no query generated!' else None

    def generate_feedback_query(self, user_query, initial_query) -> str:
        """
        Generate an improved SQLite query based on feedback of the initial query.

        :param user_query: The original user question that prompted the query generation
        :param initial_query: The original SQLite query that needs improvement
        :return: Expert feedback highlighting issues and suggested improvements
        """
        print('# Generating feedback-based query')
        if not initial_query:
            return "GOOZ"

        feedback_instructions = self.feedback_prompt_maker(user_query)
        feedback_query = call_generative_api(feedback_instructions, initial_query)
        return feedback_query.text

    def generate_improved_query(self, initial_query, feedback):
        #TODO do it tonight
        # step-1: make the system_instructions
        improved_instruction = self.improved_query_prompt_maker(feedback)
        # call Gemini AI to generate an improved query 
        improved_query = call_generative_api(improved_instruction, initial_query)
        # improved_sqlite_query = extract_code_blocks(improved_query.text)
        print('improved query :   \n', improved_query.text, '\n')
        return improved_query.text

    def generate_sqlite_query(self, user_query, complexity):
        """Orchestrates the SQLite query generation process using initial and feedback steps"""
        print('## hi from generate_sqlite_query')
        print('initial query making step')
        # initial query making step
        initial_query = self.generate_initial_query(user_query, complexity)
        if initial_query is None:
            print('Initial query generation failed...')
            return
        # print('Line 554 =>\n', initial_query)
        # feedback step
        print('feedback step ....')
        feedback = self.generate_feedback_query(user_query, initial_query)
        print(f"""## feedback: {feedback}""")
        # improved_query_prompt step
        return self.generate_improved_query(initial_query, feedback)

    def execute_sqlite_query(self, query: str):
        """Executes a SQLite query and returns the result as a DataFrame."""
        conn = sqlite3.connect(self.db_file)
        try:
            result = pd.read_sql_query(query, conn)
            # Store the full results for potential follow-up queries
            self.last_full_results = result
            return result
        except Exception as e:
            raise Exception(f"Error executing SQLite query: {str(e)}")
        finally:
            conn.close()

    def post_process_results(self, user_query, full_results):
        """
        Post-processes the full results to extract the relevant information.
        
        Args:
            user_query: The original user query
            full_results: The full results from the SQLite query
            
        Returns:
            dict: A dictionary with concise_answer and additional_info_available
        """
        # Take a sample of the results to send to the LLM (to avoid token limitations)
        sample_size = min(10, len(full_results))
        sample_results = full_results.head(sample_size)
        
        # Create the post-processing prompt
        post_processing_instructions = self.post_processing_prompt_maker(user_query, sample_results)
        
        # Call the LLM for post-processing
        post_processed = call_generative_api(post_processing_instructions, user_query)
        
        if not post_processed:
            return {
                "concise_answer": "I was able to find some results but couldn't process them properly.",
                "additional_info_available": "I have the full records if you'd like to see them."
            }
            
        return json.loads(post_processed.text)

    def analyze(self, user_query):
        print('# analyzer_says_hi')
        print('## pre-processing ...')
        cleaned_query = self.preprocess_query(user_query)
        assessment = self.assess_query_complexity(cleaned_query)
        complexity = assessment.get(
            'complexity', 'ERROR in assess_query_complexity()')
        
        if complexity in ("SIMPLE_SQLITE", "COMPLEX_SQLITE"):
            sqlite_query_to_execute = self.generate_sqlite_query(cleaned_query, complexity)
            
            try:
                query_text = json.loads(sqlite_query_to_execute).get("revised-query", 'nothing to execute')
                # Execute the query to get full records
                full_results = self.execute_sqlite_query(query_text)
                print('\nlength of the full records\t:\t', len(full_results)) 
                # Post-process the results to get a concise answer
                processed_results = self.post_process_results(cleaned_query, full_results)
                
                return {
                    "full_results": full_results,
                    "processed_results": processed_results,
                }
            except Exception as e:
                print(f"Error in analyze: {e}")
                return f"Error processing query: {str(e)}"
        
        return user_query


def main():
    try:
        # user_query = 'what are some movies starring Sean Penn?'
        # user_query = 'what is the oldest movie and its locations in the database?'
        # user_query = "What are some films made in SF made by either Spielberg or Eastwood?"
        # user_query = "has Nicole Kidman ever played in a film or series shot in San Francisco per your data?"
        user_query = "what are some films and series shot in north beach, folsom street, california st or EMbarcadero in SF?"
        # user_query = "What are some shooting locations of the film Sudden Impact? Give me all the information about the locations!"
        film_obj = SFMovieQueryProcessor(DB_FILE, user_query)

        response = film_obj.analyze(user_query)
        
        if isinstance(response, dict) and "processed_results" in response:
            print("\n=== CONCISE ANSWER ===")
            print(response["processed_results"]["concise_answer"])
            print("\n=== ADDITIONAL INFO AVAILABLE ===")
            print(response["processed_results"]["additional_info_available"])
            print("\n=== SAMPLE OF FULL RESULTS ===")
            # print(response["full_results"].head())
            # with pd.option_context('display.index', False):
                # print(result)
            print(response["full_results"].to_string(index=False))
            # print(response["full_results"])
            # print("\n=====TEST FULL RESULTS=====")
            # print(response["test_full_results"])

        else:
            print(response)
            
    except Exception as e:
        print(f"# Error in main()➡️ {e}")


if __name__ == "__main__":
    main()
