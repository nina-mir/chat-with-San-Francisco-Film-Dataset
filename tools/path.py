###############################################
# LIBRARY IMPORTS                             #
###############################################
# Import the SFMovieQueryProcessor class
from sql_converter import SFMovieQueryProcessor

import os
from dotenv import load_dotenv
import sqlite3
from google import genai
from google.genai import types, Client
from google.genai.types import (
    FunctionDeclaration,
    GenerateContentConfig,
    HttpOptions,
    Tool,
    Content,
    Part,
    ModelContent,
    UserContent, 
    FunctionResponse
)

import pandas as pd
import json
import dataclasses
import typing_extensions as typing
from pathlib import Path
import textwrap
import pprint
import re

###############################################
# Pandas setting                              #
###############################################
pd.set_option('display.max_rows', 200)
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

# init Gemini
client = Client(
    api_key=GEMINI_API_KEY,
)

# The client.models modules exposes model inferencing and model getters.
# models = client.models
###############################################
#     PATH to SQLite database established     #
#                                             #
###############################################
DB_FILE = 'sf-films-geocode.db'
db_path = Path.cwd().joinpath("..").joinpath(DB_FILE).resolve()
########################################################
# UTILITY FUNCTIONS
#######################################################


def read_json_to_dict(path):
    """
    Reads a JSON file and returns its contents as a Python dictionary.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: A Python dictionary representing the JSON data, or None if an error occurs.
    """
    try:
        with open(path, 'r') as f:
            json_data = json.load(f)
            return json_data
    except FileNotFoundError:
        print(f"Error: File not found at {path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {path}")
        return None
#######################################################
# setup the function declaration for the tool
convert_to_sqlite_declaration = read_json_to_dict('sql_converter.json')

execute_sql_query_tool = {
    "name": "execute_sql_query",
    "description": "Executes a SQL query against a SQLite database with pagination and returns results with metadata.",
    "parameters": {
        "type": "object",
        "properties": {
            "sql_query": {
                "type": "string",
                "description": "The SQL query to execute.",
            },
            "offset": {
                "type": "integer",
                "description": "The starting row number (0-based index) for pagination. Defaults to 0.",
            },
            "limit": {
                "type": "integer",
                "description": "The maximum number of rows to return per page. Defaults to 5.",
            },
        },
        "required": ["sql_query"],
    },
}

#######################################################
# set-up the tool
# FunctionDeclaration()
# tool config


system_instruction = '''
You are a helpful chatbot specializing in answering queries about film locations in San Francisco, California from 1915
to the present.

# Available Tools

## tool_1
Purpose: "nlp_2_sql_SanFranciscoFilmLocations" tool to convert user queries to SQLite queries.

## tool_2
Purpose: "execute_sql_query" tool to execute the SQLite query from tool_1 in the database.

# Query Handling Guidelines

- If the user query is about movies or TV series shot in San Francisco, or about actors, writers, directors, and production
years of such projects, call the appropriate tools to help answer their query.

- When asking clarifying questions about a user query related to San Francisco film locations, always:
1. After receiving a positive clarification from the user, include the complete original query along with the clarified information when calling the nlp_2_sql_SanFranciscoFilmLocations function.
2. Always pass the full context in the user_query parameter, combining both the original request and any additional information gained through clarification.

- If the user query could be about movies but doesn't specifically mention San Francisco, ask for clarification. For example:
  ### Example 1
  - User query: "What are some films made in 1960?"
  - You: "Is your question about films made in the city of San Francisco in the 1960s?"

  ### Example 2
  - User query: "Which director made the most films?"
  - You: "Is your question about films made in the city of San Francisco?"

# Tool Execution Process

- After tool_1 finishes executing, it will share its result as a function_response.
- If the message contains a SQLite query, you need to call tool_2 to execute the query.
- After tool_2 completes its work, it will send you its result a function_response.
- You will then share the result with the user and determine how to proceed with the conversation.

# Error Handling Guidelines

## Query Interpretation Errors
- If you're uncertain about the meaning of a user query, ALWAYS ask for clarification.
- When you're not sure if a query relates to San Francisco films, ask explicitly before proceeding.

## Database Query Errors
- If tool_1 returns an error or invalid SQL, explain to the user that there was a problem
formulating their query and try to rephrase the question.
- If tool_2 returns an error when executing SQL, inform the user about the issue in simple terms
and suggest how they might rephrase their question.

## Empty Results Handling
- If a query returns no results, explicitly tell the user no matching films were found.
- Suggest query modifications that might yield results (e.g., "No films found from 1915-1920.
Would you like to see films from the 1920s instead?")

## Recovery Strategies
- If you're unable to convert a user query into a valid database query after two attempts, offer
to help the user with a simpler or more specific question.
- For ambiguous queries, provide 2-3 specific interpretations and ask the user which one they meant.

## Query Size Limitations
- For queries that might return very large result sets, first confirm with the user if they want all
results or would prefer a limited set (e.g., "There are over 100 films matching your criteria.
Would you like me to show the 10 most recent ones?")
'''


def start_chat_session():
    """Starts and manages an interactive chat session with Gemini."""
    try:
        # Starting chat client
        tools = types.Tool(function_declarations=[
                           convert_to_sqlite_declaration, execute_sql_query_tool])
        config = types.GenerateContentConfig(
            tools=[tools],
            system_instruction=system_instruction,
            temperature=0.1
        )

        chat = client.chats.create(
            model=MODEL_NAME,
            config=config
        )

        print(f"Starting chat with {MODEL_NAME}. Type exit, quit, end, aus or aufhören to end.")
        print("-" * 30)

        while True:
            try:
                user_input = input("You: ")
            except KeyboardInterrupt:
                print("\nExiting chat session...")
                break
            except EOFError:  # Handles Ctrl+D
                print("\nExiting chat session...")
                break

            # Exit conditions
            if user_input.lower() in ["exit", "quit", "aus", "end", "aufhören"]:
                print("Exiting chat session...")
                break

            # Prevent sending empty messages
            if not user_input.strip():
                continue

            # Send message to Gemini and process any function calls
            try:
                response = chat.send_message(user_input)
                
                # Process the response
                if hasattr(response, 'text') and response.text:
                    print(f"Gemini: {response.text}")
                    continue  # If there's text, just display it and continue
                
                # Check for function calls
                function_call = None
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_call = part.function_call
                            break
                
                if not function_call:
                    print("Gemini: (No response or function call provided)")
                    continue
                    
                print(f"Function to call: {function_call.name}")
                
                # Handle the NLP to SQL conversion
                if function_call.name == "nlp_2_sql_SanFranciscoFilmLocations":
                    function_args = function_call.args
                    user_query = function_args.get('natural_language_query')
                    print(f"Converting query: {user_query}")
                    
                    # Call your SQL conversion tool
                    tool_1 = SFMovieQueryProcessor(db_path, user_query)
                    sql_result = tool_1.analyze()
                    
                    # Create and send function response
                    function_response_part = Part.from_function_response(
                        name="nlp_2_sql_SanFranciscoFilmLocations",
                        response={"result": sql_result}
                    )
                    
                    # Send the result back to continue the conversation
                    response = chat.send_message(function_response_part)
                    
                    # Now check if we need to execute an SQL query
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                exec_function_call = part.function_call
                                if exec_function_call.name == "execute_sql_query":
                                    sql_query = exec_function_call.args.get("sql_query")
                                    offset = exec_function_call.args.get("offset", 0)
                                    limit = exec_function_call.args.get("limit", 5)
                                    
                                    # Execute the SQL query
                                    print(f"Executing SQL: {sql_query}")
                                    try:
                                        conn = sqlite3.connect(db_path)
                                        df = pd.read_sql_query(sql_query, conn)
                                        
                                        # Apply pagination
                                        total_rows = len(df)
                                        df_paginated = df.iloc[offset:offset+limit]
                                        
                                        # Convert to dict for response
                                        results = df_paginated.to_dict(orient='records')
                                        
                                        # Create metadata
                                        metadata = {
                                            "total_rows": total_rows,
                                            "offset": offset,
                                            "limit": limit,
                                            "returned_rows": len(results)
                                        }
                                        
                                        # Create and send response
                                        sql_response_part = Part.from_function_response(
                                            name="execute_sql_query",
                                            response={
                                                "results": results,
                                                "metadata": metadata
                                            }
                                        )
                                        
                                        # Send the result back and show the model's interpretation
                                        final_response = chat.send_message(sql_response_part)
                                        print(f"Gemini: {final_response.text}")
                                        
                                    except Exception as e:
                                        error_msg = f"SQL execution error: {str(e)}"
                                        print(f"Error: {error_msg}")
                                        
                                        # Inform the model about the error
                                        error_response_part = Part.from_function_response(
                                            name="execute_sql_query",
                                            response={"error": error_msg}
                                        )
                                        error_response = chat.send_message(error_response_part)
                                        print(f"Gemini: {error_response.text}")
                                    finally:
                                        if 'conn' in locals():
                                            conn.close()
                                else:
                                    # Handle unexpected function call
                                    print(f"Unexpected function call: {exec_function_call.name}")
                                    print(f"Gemini: {response.text}")
                                break
                        else:
                            # No function call found
                            print(f"Gemini: {response.text}")
                else:
                    # Handle direct execute_sql_query or other function calls
                    print(f"Direct function call: {function_call.name}")
                    if function_call.name == "execute_sql_query":
                        # Process direct SQL execution request
                        sql_query = function_call.args.get("sql_query")
                        offset = function_call.args.get("offset", 0)
                        limit = function_call.args.get("limit", 5)
                        
                        # Execute SQL (same code as above)
                        # ...
                    else:
                        print(f"Unhandled function call: {function_call.name}")

            except Exception as e:
                print(f"\nAn error occurred: {e}")
                
    except Exception as e:
        print(f"\nFailed to initialize the chat model or session: {e}")

'''
 def start_chat_session():
    """Starts and manages an interactive chat session with Gemini."""
    try:
        # Starting chat client
        tools = types.Tool(function_declarations=[
                           convert_to_sqlite_declaration, execute_sql_query_tool])
        config = types.GenerateContentConfig(
            tools=[tools],
            system_instruction=system_instruction,
            temperature=0.1
        )

        chat = client.chats.create(
            model=MODEL_NAME,
            config=config
        )

        print(
            f"Starting chat with {MODEL_NAME}. Type exit, quit, end, aus or aufhören to end.")
        print("-" * 30)

        while True:
            try:
                user_input = input("You: ")
            except KeyboardInterrupt:
                print("\nExiting chat session...")
                break
            except EOFError:  # Handles Ctrl+D
                print("\nExiting chat session...")
                break

            # Exit conditions
            if user_input.lower() in ["exit", "quit", "aus", "end", "aufhören"]:
                print("Exiting chat session...")
                break

            # Prevent sending empty messages
            if not user_input.strip():
                continue

            # Send message to Gemini and handle response (same method)
            try:
                response = chat.send_message(user_input)
                print(f"response text part is\n: {response.text}")
                print(f"full response is\n: {response}")

                if response.candidates[0].content.parts[0].function_call:
                    function_call = response.candidates[0].content.parts[0].function_call
                    print(f"Function to call: {function_call.name}")
                    print("_" * 35)  # Separator for clarity
                    if function_call.name == "nlp_2_sql_SanFranciscoFilmLocations":
                        function_args = function_call.args
                        user_query = function_args.get(
                            'natural_language_query')
                        print(f"user message: {user_query}")
                        print("-" * 35)  # Separator for clarity
                        #  In your app, you would call your function here:
                        # user_query = 'what are some movies made in 1920s?'
                        tool_1 = SFMovieQueryProcessor(db_path, user_query)
                        result = tool_1.analyze()
                        print('Ergebniss vom path.py ist\n', result)


                       # Create the function response part directly
                        function_response_part = Part.from_function_response(
                            name="nlp_2_sql_SanFranciscoFilmLocations",
                            response={
                                "result": result
                            }
                        )

                        # Send the function response part to the model
                        response_2 = chat.send_message(function_response_part)
                        print(
                            f"\nGemini Response (after SQL execution tool): {response_2.candidates[0].content.parts[0]}")
                        # Check if Gemini called the execute_sqlite_query tool
                        if response_2.candidates[0].content.parts[0].function_call:
                            function_call_2 = response_2.candidates[0].content.parts[0].function_call
                            if function_call_2.name == 'execute_sql_query':
                                # Simulate the execution of the execute_sqlite_query tool
                                # In a real application, you would call your Python function here
                                sql_query = function_call_2.args.get(
                                    "sql_query")
                                offset = function_call_2.args.get("offset", 0)
                                limit = function_call_2.args.get("limit", 5)
                                print(
                                    f"\nExecuting execute_sqlite_query with query: '{sql_query}', offset: {offset}, limit: {limit}")
                            else:
                                print(
                                    "Gemini did not call execute_sqlite_query as expected.")
                        else:
                            print(
                                "Gemini did not call a function after receiving the SQL query.")
                    else:
                        print("Gemini did not call nlp_to_sqlite as expected.")
                else:
                    print("No function call found in the response.")

                 # Use textwrap for potentially long responses
                # wrapped_text = textwrap.fill(response.text, width=80)
                # print(f"Gemini:\n{wrapped_text}")
                # print(response)
                # print(response.text)
                # print("-" * 30)  # Separator for clarity

            except Exception as e:
                print(f"\nAn error✂️ occurred in 💬: {e}")
                print("There might be an issue with the API call or your connection.")
                # Optional: break here if you want the chat to end on error
                # break

    except Exception as e:
        print(f"\n📛Failed📛 to initialize the chat model⚠️ or session⚠️: {e}")
        print("Please check your API key, model name, and ensure the 'google-genai'📛package is correctly installed.")
'''


start_chat_session()

# data = read_json_to_dict('sql_converter.json')

# print(data)



# try:
#     user_query = 'what are some movies made in 1920s?'
#     test = SFMovieQueryProcessor(db_path, user_query)
#     result = test.analyze()
#     print('Ergebniss vom path.py iss\n', result)

# except Exception as e:
#         print(f"# FEHLER in test ➡️ {e}")


# from  pathlib import Path

# DB_FILE = 'sf-films-geocode.db'

#  db_path = Path.cwd().joinpath("..").joinpath(DB_FILE).resolve()

# print(db_path)



# A mock FunctionDeclaration example
# convert_to_sqlite_declaration = {
#     "name": "convertToSQLite_SanFranciscoFilmLocations",
#     "description": "Converts a user's natural language query about film locations in San Francisco into a valid SQLite query string.",
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "natural_language_query": {
#                 "type": "string",
#                 "description": "The user's question or request about San Francisco film locations in plain English."
#             }
#         },
#         "required": ["natural_language_query"]
#     }
# }
