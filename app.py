###############################################
# LIBRARY IMPORTS
###############################################
import os
from dotenv import load_dotenv
# import glob
import sqlite3
from google import genai
from google.genai import types, Client
# import pandas as pd
import json
import dataclasses
import typing_extensions as typing
import pathlib
import textwrap
import pprint
import re

# from IPython.display import HTML, Markdown, display
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
# MAIN CLASS DEFINITION
###############################################


class SFMovieQueryProcessor:
    """
    A class represnting the processing step of the user query
    in a SQLite query or a Pandas
    """

    def __init__(self, db_file: str, user_query: str):
        self.db_file = db_file
        self.user_query = user_query
        self.db_structure = self._get_db_structure()
        self.sample_data = self._get_sample_data()
        # self.output_folder = self.create_output_folder()
        # os.makedirs(self.output_folder, exist_ok=True)

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
        TODO: add LLM to this step
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

        print(f"# Raw query: {raw_query}")
        print(f"# Preprocessed query: {cleaned_query}")
        return cleaned_query

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

    def initial_query_prompt_maker(self, complexity: str) -> str:
        """
        Creates a structured prompt for generating optimized SQLite queries based on user questions
        and previously determined complexity level. Ensures queries perform case-insensitive searches.

        :param user_query: The user's original question to be answered via SQL
        :param complexity: The determined complexity level (SIMPLE_SQLITE or COMPLEX_SQLITE)
        :return: A formatted prompt string for the LLM with instructions to generate a SQLite query
        """

        initial_query_prompt = f"""
    # SQLite Query Generator for San Francisco Film Database

    ## User Request
    Generate a SQLite query to precisely answer the user_input.

    ## Query Parameters
    - Complexity Level: {complexity}
    - Query Type: {'Simple direct lookup' if complexity == 'SIMPLE_SQLITE' else 'Complex multi-condition or aggregation'}
    - Search Type: Case-insensitive

    ## Database Context

    ### Database Structure
    {json.dumps(self.db_structure, indent=2)}

    ### Sample Data from sf_film_data table
    {json.dumps(self.sample_data, indent=2)}

    ## Technical Requirements

    You are a world-class SQLite expert. Your task is to create a precise, efficient, and properly optimized query that:

    1. **Matches Complexity Level**: 
    - {'Use simple WHERE clauses and avoid unnecessary JOINs or subqueries' if complexity == 'SIMPLE_SQLITE' else 'Utilize appropriate JOINs, subqueries, aggregations, or multiple conditions as needed'}

    2. **Ensures Accuracy**:
    - Validate column names against the schema
    - Handle potential NULL values appropriately
    - Use proper data type handling (TEXT, INTEGER, etc.)

    3. **Implements Case-Insensitive Search**:
    - Use LOWER() or UPPER() functions for text comparisons
    - Example: WHERE LOWER(column_name) LIKE LOWER('%search_term%')
    - Apply case-insensitive search to all text-based filtering conditions
    - Ensure case-insensitivity doesn't adversely impact query performance

    4. **Follows Best Practices**:
    - Use descriptive aliases for readability
    - Properly quote string literals
    - Use parameterized queries when appropriate
    - Follow SQLite syntax conventions precisely

    5. **Optimizes Performance**:
    - Select only necessary columns
    - Use appropriate indexing hints if needed
    - Avoid full table scans when possible
    - Structure WHERE clauses for efficiency

    6. **Clarifies Intent**:
    - Include explanatory comments above complex logic
    - Note any assumptions made about the data
    - Explain any special handling or edge cases

    ## Response Format
    Provide only the final, executable SQLite query code between #begin and #end markers:

    #begin
    -- Your optimized SQLite query here with comments
    -- Ensure all text searches are case-insensitive
    #end
    """
        return initial_query_prompt

    def feedback_prompt_maker(self, user_query: str) -> str:
        """
        Creates a structured prompt for obtaining expert feedback on a generated SQLite query.

        :param user_query: The original user question that prompted the query generation
        :param initial_query: The SQLite query to be evaluated from initial step
        :return: A formatted prompt string for the LLM to provide feedback
        """

        feedback_prompt = f"""
    # SQLite Query Review: Expert Feedback

    ## Context
    - User Query: "{user_query}"
    - Generated SQLite Query will be given to you. 
    ```

    ## Reviewer Role
    You are a senior database engineer specializing in SQLite optimization. Your task is to provide actionable feedback on the query above. Be thorough but prioritize feedback that would significantly improve the query.

    ## Evaluation Criteria

    1. **Correctness & Accuracy**
    - Does the sqlite query correctly address the user's question?
    - Are there logical errors or misinterpretations?
    - Will it return the expected data?

    2. **Performance Optimization**
    - Are there inefficient patterns (unnecessary scans, poor join order)?
    - Could indexes be better utilized?
    - Is the query unnecessarily complex for the task?

    3. **SQLite-Specific Considerations**
    - Does the query use SQLite dialect appropriately?
    - Are there SQLite-specific optimizations that could be applied?
    - Does it handle SQLite's type affinity system correctly?

    4. **Robustness & Safety**
    - How does it handle NULL values, empty results, or edge cases?
    - Is text searching properly case-insensitive?
    - Are there potential injection risks?

    5. **Readability & Maintainability**
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

    def improved_query_prompt_maker(self, initial_query: str, feedback:str) -> str:
        """Generates a prompt for improving a SQLite query based on given feedback.
    
        Constructs a structured prompt that guides an LLM to revise an initial SQL query
        by incorporating specific feedback. The prompt includes clear instructions,
        formatting requirements, and markers for the response.

        Args:
            initial_query (str): The original SQLite query that needs improvement.
            feedback (str): Feedback describing the issues or desired improvements
                        for the initial query.

        Returns:
            str: A well-structured prompt that includes:
                - Task description
                - Step-by-step instructions
                - Provided feedback
                - Initial query (formatted as code)
                - Required output format with markers

        Example:
            >>> prompt_maker.improved_query_prompt_maker(
            ...     "SELECT * FROM users",
            ...     "Need to limit columns and add a WHERE clause"
            ... )
            # Returns a structured prompt containing both the query and feedback
            # with instructions for improvement
        """
        improved_query_prompt = f"""
        # TASK
        Revise the SQLite query based on the provided feedback to create an improved, correct query.
        
        # INSTRUCTIONS
        1. Carefully analyze the feedback and initial query
        2. Identify all issues mentioned in the feedback
        3. Make only the necessary changes to address the feedback
        4. Maintain the original query's purpose and intent
        5. Ensure the revised query follows SQLite syntax rules
        
        # FEEDBACK
        {feedback}
        
        # INITIAL QUERY
        ```sql
        {initial_query}
        ```
        
        # OUTPUT FORMAT
        - Provide ONLY the revised SQLite query
        - Enclose the entire query between #begin and #end markers
        - Do not include any explanations or commentary
        - If no changes are needed, return the original query
        
        # REVISED QUERY
        #begin
        #end
        """
        return improved_query_prompt

    def generate_initial_query(self, user_query, complexity):
        """Generate the initial SQLite query based on user input and complexity"""

        print('# Generating initial query')
        initial_step_instructions = self.initial_query_prompt_maker(complexity)
        initial_query = call_generative_api(initial_step_instructions, user_query)

        if not initial_query:
            return None

        query = json.loads(initial_query.text).get('query', 'no query generated!')
        return query if query != 'no query generated!' else None

    def generate_feedback_query(self, user_query, initial_query):
        """Generate an improved SQLite query based on feedback of the initial query"""
        print('# Generating feedback-based query')
        if not initial_query:
            return "GOOZ"

        feedback_instructions = self.feedback_prompt_maker(user_query)
        feedback_query = call_generative_api(feedback_instructions, initial_query)
        return feedback_query.text

    def generate_improved_query(self, initial_query, feedback):
        #TODO do it tonight
        return None
    def generate_sqlite_query(self, user_query, complexity):
        """Orchestrates the SQLite query generation process using initial and feedback steps"""
        print('## hi from generate_sqlite_query')
        ##############################################
        # TODO-add the preprocessing step here!      #
        ##############################################
        # initial query making step
        initial_query = self.generate_initial_query(user_query, complexity)
        initial_query = extract_code_blocks(initial_query)
        # feedback step
        feedback =  self.generate_feedback_query(user_query, initial_query[0])
        # improved_query_prompt step
        return self.improved_query_prompt_maker(initial_query[0], feedback)
        # improved_query = self.generate_improved_query(initial_query, feedback)


    def analyze(self, user_query):
        print('# analyzer_says_hi')
        assessment = self.assess_query_complexity(user_query)
        complexity = assessment.get(
            'complexity', 'ERROR in assess_query_complexity()')
        if complexity in ("SIMPLE_SQLITE", "COMPLEX_SQLITE"):
            return self.generate_sqlite_query(user_query, complexity)
            # sqlite_system_instructions = self.initial_query_prompt_maker(
            #     complexity)
            # initial_query = call_generative_api(sqlite_system_instructions, user_query)
            # query = json.loads(initial_query.text).get('query', 'no query generated!')
            # return extract_code_blocks(query)
            # let's do feedback
        return user_query


def main():
    try:
        # TODO: Update pip to the latest version
        # TODO: Check if the db file exits + raise error if not

        # user_query = 'what are some movies starring Sean Penn?'
        user_query = 'what is the oldest movie and its locations in the database?'
        # user_query = "What are some films made in SF made by either Spielberg or Eastwood?"
        # user_query = "was ist das?"
        film_obj = SFMovieQueryProcessor(DB_FILE, user_query)

        # print(json.dumps(film_obj.db_structure, indent=2))

        response = film_obj.analyze(user_query)

        print(response)
    except Exception as e:
        print(f"# Error in main()➡️ {e}")


if __name__ == "__main__":
    main()





    # def generate_sqlite_query(self, user_query, complexity):
    #     """Generate a SQLite query"""
    #     print('hi from generate_sqlite_query')
    #     # initial step
    #     initial_step_instructions = self.initial_query_prompt_maker(complexity)
    #     initial_query = call_generative_api(initial_step_instructions, user_query)
    #     # print(initial_query)
    #     if not initial_query:
    #         return "GOOZ"

    #     query = json.loads(initial_query.text).get('query', 'no query generated!')

    #     # feedback step
    #     if query != 'no query generated!':
    #         feedback_instructions = self.feedback_prompt_maker(user_query)
    #         feedback_query = call_generative_api(feedback_instructions, query)
    #         return feedback_query.text
