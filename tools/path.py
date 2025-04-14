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
from google.genai.types import HttpOptions, ModelContent, Part, UserContent
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
    http_options=HttpOptions(api_version="v1")
)

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
###############################################
###############################################
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
# set-up the chat                                     #
#######################################################
###############################################
# Chat Function
###############################################


def start_chat_session():
    """Starts and manages an interactive chat session with Gemini."""
    try:
        # Model initialization is done above
        # Starting chat client

        # chat = client.chats.create(model=MODEL_NAME)

        chat = client.chats.create(
            model="gemini-2.0-flash-001",
            history=[
                UserContent(parts=[Part(text="Hello")]),
                ModelContent(
                    parts=[
                        Part(text="Great to meet you. What would you like to know?")],
                ),
            ],
        )

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
                # Use textwrap for potentially long responses
                wrapped_text = textwrap.fill(response.text, width=80)
                print(f"Gemini:\n{wrapped_text}")
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
