###############################################
# LIBRARY IMPORTS                             #
###############################################
from sql_converter import SFMovieQueryProcessor
import os
from dotenv import load_dotenv
# import glob
import sqlite3
from google import genai
from google.genai import types, Client
from google.genai.types import ModelContent, Part, UserContent
from google.genai.types import (
    FunctionDeclaration,
    GenerateContentConfig,
    HttpOptions,
    Tool,
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

MODEL_NAME = 'gemini-2.0-flash'
# Only run this block for Gemini Developer API
# Configure Gemini
client = genai.Client(
    api_key=GEMINI_API_KEY,
)

    # http_options=HttpOptions(api_version="v1")

# The client.models modules exposes model inferencing and model getters.
# models = client.models
###############################################
#     PATH to SQLite database established     #
#                                             #
#       import the SFMovieQueryProcessor      #
#                                             #
###############################################
DB_FILE = 'sf-films-geocode.db'
db_path = Path.cwd().joinpath("..").joinpath(DB_FILE).resolve()
########################################################
#######################################################
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
            # read_data = f.read()
            json_data = json.load(f)
            return json_data
    except FileNotFoundError:
        print(f"Error: File not found at {path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {path}")
        return None
#######################################################
# First, properly define your function schema for Gemini

read_json_to_dict = {
    "name": "read_json_to_dict",
    "description": "Reads a JSON file and returns its contents as a Python dictionary.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path to the JSON file."
            }
        },
        "required": ["file_path"]
    }
}

# Then, implement the actual function that will be called


def read_json_to_dict_impl(file_path):
    """
    Reads a JSON file and returns its contents as a Python dictionary.
    """
    try:
        with open(file_path, 'r') as f:
            json_data = json.load(f)
            return json_data
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {file_path}")
        return None


# Define the function schema for Gemini
# First, define your actual implementation function
def convert_to_sqlite_sf_film(natural_language_query: str) -> str:
    """
    Implementation of the function that would normally process the result.
    For now, just returns the input to complete the setup.
    """
    return {"generated_query": natural_language_query}


# Then create a proper FunctionDeclaration
convert_to_sqlite_declaration = {
    "name": "convertToSQLite_SanFranciscoFilmLocations",
    "description": "Converts a user's natural language query about film locations in San Francisco into a valid SQLite query string.",
    "parameters": {
        "type": "object",
        "properties": {
            "natural_language_query": {
                "type": "string",
                "description": "The user's question or request about San Francisco film locations in plain English."
            }
        },
        "required": ["natural_language_query"]
    }
}


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
        model=MODEL_NAME,
        contents=user_query,
        config=types.GenerateContentConfig(
            system_instruction=system_instructions,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

    return response


#######################################################
# set-up the tool
# FunctionDeclaration()
# tool config
#######################################################
# set-up the chat                                     #
#######################################################
# Chat Function
###############################################


system_ = '''
You are a helpful chatbot who has a specialty in answering queries about locations of
films shot in San Francisco, California since 1915 till now. You have access to a tool that
converts natural language queries to their equivalent in SQLIte for use in the tool that you have.
If the user query is about movies or TV series shot in San Francisco, or actors, writers, directors
and years of film projects, you could call the tool to help the user with their query.
'''


def start_chat_session():
    """Starts and manages an interactive chat session with Gemini."""
    try:
        # Model initialization is done above
        # Starting chat client

        # chat = client.chats.create(model=MODEL_NAME)

        # config = {
        #     "tools": [converter_tool],
        #     "automatic_function_calling": {"disable": True},
        #     "temperature": 0.2
        #     # Force the model to call 'any' function, instead of chatting.
        #     # "tool_config": {"function_calling_config": {"mode": "any"}},
        # }


        # Generation Config with Function Declaration
        tools = types.Tool(function_declarations=[convert_to_sqlite_declaration])
        config = types.GenerateContentConfig(
            tools=[tools],
            system_instruction=system_
        )

        chat = client.chats.create(
            model="gemini-2.0-flash-001",
            config=config
        )


# history=[
#                 UserContent(parts=[Part(text="Hello")]),
#                 ModelContent(
#                     parts=[
#                         Part(text="Great to meet you. What would you like to know?")],
#                 ),
#             ],

        print(
            f"Starting chat with {MODEL_NAME}. Type 'exit' or 'quit' to end.")
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
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting chat session...")
                break

            # Prevent sending empty messages
            if not user_input.strip():
                continue

            # Send message to Gemini and handle response (same method)
            try:
                response = chat.send_message(user_input)

                if response.candidates[0].content.parts[0].function_call:
                    function_call = response.candidates[0].content.parts[0].function_call
                    print(f"Function to call: {function_call.name}")
                    print(f"Arguments: {function_call.args}")
                    print(f"total function call message: {function_call}")
                    print("-" * 35)  # Separator for clarity
                    #  In a real app, you would call your function here:
                    #  result = get_current_temperature(**function_call.args)
                else:
                    print("No function call found in the response.")

                 # Use textwrap for potentially long responses
                # wrapped_text = textwrap.fill(response.text, width=80)
                # print(f"Gemini:\n{wrapped_text}")
                print(response)
                print(response.text)
                # print(function_call)

                print("-" * 30)  # Separator for clarity

            except Exception as e:
                print(f"\nAn error occurred: {e}")
                print("There might be an issue with the API call or your connection.")
                # Optional: break here if you want the chat to end on error
                # break

    except Exception as e:
        print(f"\nFailed to initialize the chat model or session: {e}")
        print("Please check your API key, model name, and ensure the 'google-genai' package is correctly installed.")


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

start_chat_session()

# data = read_json_to_dict('sql_converter.json')

# print(data)
