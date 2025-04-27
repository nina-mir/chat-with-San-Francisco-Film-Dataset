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
from pathlib import Path
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

db_path = Path.cwd().joinpath("..").joinpath(DB_FILE).resolve()
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

    try:
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
    except Exception as e:
        print(f"🫥Fehler in sql_converter.py file😑: {e}")
        return None


def extract_code_blocks(llm_response: str):
    """Extracts multiple code blocks from the LLM response."""
    code_blocks = re.findall(r"#begin(.*?)#end", llm_response, re.DOTALL)
    if not code_blocks:
        # Fallback to a more lenient extraction method if no code blocks are found
        code_blocks = re.findall(r"```python(.*?)```", llm_response, re.DOTALL)
        if not code_blocks:
            raise ValueError("No valid code blocks found in the LLM response.")
    return [block.strip() for block in code_blocks]


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
        self.conn = None
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
        self.conn = conn
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
        # to-do : call GEmini to preprocess this result.
        # get rid of street, city of SF, any mention of San Francisco
        # Convert to lowercase
        # cleaned_query = raw_query.lower()
        # # Remove "in san francisco" as the data is specific to SF
        # cleaned_query = cleaned_query.replace(
        #     "in san francisco", "").strip()
        # cleaned_query = cleaned_query.replace(
        #     "in sf", "").strip()
        # print(f"# Raw query: {raw_query}")
        # print(f"# Preprocessed query: {cleaned_query}")
        # return cleaned_query
        try:
            system_instructions = self.generate_preprocessing_prompt()
            response = call_generative_api(system_instructions, raw_query)
            # print('pre_processing_result ➡️ ', response.text)
            return response.text
        except Exception as e:
            error_message = f"preprocessing error occured: {e}"
            print(error_message)
            return error_message

    def generate_preprocessing_prompt(self) -> str:
        """
        Generate system instructions for Gemini AI to handle movie location queries.

        Returns:
            Dictionary containing system instructions
        """
        system_instructions = f"""
        You are a specialized movie and TV location database assistant focused on filming locations.
        Your job is to preprocess the user query about filming locations in San Francisco 
        to a concise and precise query.

        Important preprocessing rules:
        1. When handling queries about locations, remove any mention to "San Francisco" city, "SF", or any reference to 
        state of "California" in your responses.
        2. When referring to locations, use only the base name without street suffixes (e.g., use "Market" instead of "Market Street").
        3. When referring to time, only refer to years. (e.g., convert "20th centurty" to "1900 to 1999" but do not change 1940s).
        
        
        Sample transformations to follow:
        - "What movies were filmed at Golden Gate Park in San Francisco?" → "What movies were filmed at Golden Gate Park?"
        - "TV shows shot on Lombard Street" → "TV shows shot on Lombard"
        - "Find TV shows shot on Octavia Boulevard in the 1940s and 1950s" → "Find episodes shot on Octavia in the 1940s and 1950s"
        - "Films made on Geary Boulevard in SF" → "Films made on Geary"
        - "Films made on Folsom street" → "Films made on Folsom"
        - "Find Films made on California street starring Clint Eastwood" → "Films made on California starring Clint Eastwood"
        - "Find films made in March 2009 in Presidio Park in the city of SF" → "Find films made in 2009 in Presidio Park"
        """

        return system_instructions

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
        - ALWAYS use SELECT * to retrieve all columns from each matching record UNLESS user explicitly requests unique values
        - When uniqueness is requested, use SELECT DISTINCT on the relevant columns only
        - This distinction is critically important as we'll post-process the results differently

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
        - When the user explicitly asks for unique/distinct items, use DISTINCT on the appropriate columns
        - Examples: "unique films", "distinct locations", "list all different directors"
        - For aggregations, ensure proper handling of distinct/non-distinct as needed
        - When uniqueness is not specified, return full records without DISTINCT

        6. **Follows Best Practices**:
        - Use descriptive aliases for readability
        - Properly quote string literals
        - Use parameterized queries when appropriate
        - Follow SQLite syntax conventions precisely

        7. **Optimizes Performance**:
        - Use appropriate indexing hints if needed
        - Avoid full table scans when possible
        - For queries requesting unique items (e.g., "list all unique films"), use DISTINCT with relevant columns
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
        - Query: "How many film or series were shot in 2015?" → Intent: Find total count of projects shot by time within a specific year
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
        print('assess : ', response.text)
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
    - IMPORTANT: Does the query use SELECT * to retrieve all columns for post-processing in general cases?
    - EXCEPTION: For queries explicitly requesting unique/distinct values, does it use DISTINCT on appropriate columns?
    - Recognize when the user is asking for unique items (using terms like "unique," "distinct," "different") and verify the query handles this correctly

    2. **Correctness & Accuracy**
    - Does the sqlite query correctly address the user's question?
    - Are there logical errors or misinterpretations?
    - Will it return the expected data?
    - If the user asks for unique values, does the query properly implement DISTINCT?

    3. **Performance Optimization**
    - Are there inefficient patterns (unnecessary scans, poor join order)?
    - Could indexes be better utilized?
    - Is the query unnecessarily complex for the task?
    - For DISTINCT queries, is DISTINCT applied efficiently to only necessary columns?

    4. **SQLite-Specific Considerations**
    - Does the query use SQLite dialect appropriately?
    - Are there SQLite-specific optimizations that could be applied?
    - Does it handle SQLite's type affinity system correctly?
    - Does it understand that SQLite requires LOWER() for case-insensitive searches?

    5. **Robustness & Safety**
    - How does it handle NULL values, empty results, or edge cases?
    - Is text searching properly case-insensitive?
    - Are there potential injection risks?
    - Does it handle the distinction between returning all records vs. unique records appropriately?

    6. **Readability & Maintainability**
    - Is the query well-formatted and easy to understand?
    - Are there helpful comments explaining complex logic?
    - Could variable naming or structure be improved?
    - Are there clear comments indicating why DISTINCT is or isn't being used?

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
        1. CRITICAL: ENSURE THE QUERY RETRIEVES APPROPRIATE RECORDS:
           - In general cases: USE "SELECT *" TO RETRIEVE FULL RECORDS
           - For explicit unique/distinct requests: USE "SELECT DISTINCT" on relevant columns
           - Determine which approach to use based on whether the user query contains terms like "unique", "distinct", "different"

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
        - Ensure there is no semi-colon at the end of your result
        - BALANCE REQUIREMENTS: Use "SELECT *" for general queries, but appropriately use DISTINCT when uniqueness is explicitly requested

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
        # print(initial_step_instructions) ⬅️why is this here
        # return     ⬅️why is this here
        initial_query = call_generative_api(
            initial_step_instructions, user_query)

        if not initial_query:
            return None

        query = json.loads(initial_query.text).get(
            'query', 'no query generated!')
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
        feedback_query = call_generative_api(
            feedback_instructions, initial_query)
        return feedback_query.text

    def generate_improved_query(self, initial_query, feedback):
        # TODO do it tonight
        # step-1: make the system_instructions
        improved_instruction = self.improved_query_prompt_maker(feedback)
        # call Gemini AI to generate an improved query
        improved_query = call_generative_api(
            improved_instruction, initial_query)
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
        # print(f"""## feedback: {feedback}""")
        # improved_query_prompt step
        return self.generate_improved_query(initial_query, feedback)

    def analyze(self):
        print('# analyzer_says_hi')
        print('## pre-processing ...')
        user_query = self.user_query

        print('user query received in the sql_converter is :  ', user_query)

        cleaned_query = self.preprocess_query(user_query)
        assessment = self.assess_query_complexity(cleaned_query)
        complexity = assessment.get(
            'complexity', 'ERROR in assess_query_complexity()')

        if complexity in ("SIMPLE_SQLITE", "COMPLEX_SQLITE"):
            sqlite_query_to_execute = self.generate_sqlite_query(
                cleaned_query, complexity)

            try:
                query_text = json.loads(sqlite_query_to_execute).get(
                    "revised-query", 'nothing to execute')
                return query_text
            except Exception as e:
                print(f"Error in analyze: {e}")
                return f"Error processing query: {str(e)}"
        else:
            return ['pandas_tool_needed', user_query]

        # return user_query


if __name__ == '__main__':
    try:
        user_query = [
            'what are some movies made in 1920s?',
            'find films in north beach sf ca', 
            'Find films made by Spielberg in Union Square and Embarcadero and Great Highway in 1999 in California and Northern America'
        ]
        for query in user_query:
            test = SFMovieQueryProcessor(db_path, query)
            pp = test.preprocess_query(query)
            print(f"major ergebniss ist: {pp}")
        # result = test.analyze()
        # print('test results is\n', result)
    except Exception as e:
        print(f"# Error in test ➡️ {e}")
