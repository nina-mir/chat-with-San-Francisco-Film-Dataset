###############################################
# LIBRARY IMPORTS                             #
###############################################
# Import the SFMovieQueryProcessor class
from sql_converter import SFMovieQueryProcessor
# Import execute_sql_query method
from sql_executor import execute_sql_query

import traceback, os, time, re
from dotenv import load_dotenv
from google import genai
from google.genai import types, Client
from google.genai.types import Part 
# (
#     FunctionDeclaration,
#     GenerateContentConfig,
#     HttpOptions,
#     Tool,
#     Content,
#     Part,
#     ModelContent,
#     UserContent,
#     FunctionResponse
# )

# import pandas as pd
import json
# import dataclasses
import typing_extensions as typing
from pathlib import Path
import textwrap
# import pprint

###############################################
# Pandas setting                              #
###############################################
# pd.set_option('display.max_rows', 200)
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



# array of keywords to end the chat session
terminate_session = ["exit", "quit", "aus", "end", "aufhören"]

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

def read_markdown_file(path) -> str:
    """
    Reads a markdown file and returns its contents in utf8 encoding

    Args:
        file_path (str): The path to the .md file.

    Returns:
        str
    """
    with open(path, 'r', encoding='utf8') as file:
        return file.read()

def log_chat_responses_to_file(response, path='response.log'):
    with open(path, 'a', encoding='utf8') as log:
        log.write(time.asctime())
        text = f"{response}"
        log.write(f"\n{textwrap.fill(text, width=80)}\n\t.....\t....")
        # log.write(response.parsed)
        log.write('\n\n')

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
# the followwing Gemini prompt is contained in system_insturction.md file 
system_instruction = read_markdown_file('system_instruction.md')

# Define the process_function_call helper function
def process_function_call(function_call, chat):
    """Process different types of function calls and return the response"""
    if function_call.name == "nlp_2_sql":
        # Process NLP to SQL
        user_query = function_call.args.get('natural_language_query')
        print(f"Converting query: {user_query}")

        tool_1 = SFMovieQueryProcessor(db_path, user_query)
        sql_result = tool_1.analyze()
        print(f"line 157-path.py➡️{sql_result}")
        # raise Exception('this is line 158');

        if isinstance(sql_result, str):
            # we received either an error or a SQLite query
            function_response = Part.from_function_response(
                name="nlp_2_sql",
                response={"result": sql_result}
            )
        elif isinstance(sql_result, list):
            print(f"line 167-path.py➡️{sql_result[0].upper()}")
            function_response = Part.from_function_response(
                name="nlp_2_sql",
                response={"result": sql_result[0] }
            )

        return chat.send_message(function_response)

    elif function_call.name == "execute_sql_query":
        # Execute SQL query
        sql_query = function_call.args.get("sql_query")
        offset = function_call.args.get("offset", 0)
        limit = function_call.args.get("limit", 5)

        print(f"Executing SQL: {sql_query}")
        try:
            sql_exec_result = execute_sql_query(sql_query, offset, limit)
            print(f"SQL execution result: {sql_exec_result}")

            function_response = Part.from_function_response(
                name="execute_sql_query",
                response=sql_exec_result
            )
        except Exception as e:
            error_msg = f"SQL execution error: {str(e)}"
            print(f"Error: {error_msg}")

            function_response = Part.from_function_response(
                name="execute_sql_query",
                response={"error": error_msg}
            )

        return chat.send_message(function_response)

    else:
        print(f"Unknown function call: {function_call.name}")
        return None




def start_chat_session():
    """Starts and manages an interactive chat session with Gemini."""
    try:
        error_recovery = False
        max_retries = 3
        retry_count = 0
        current_user_input = ""
        
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

        print("""
              (●'◡'●): hiya! you are now chatting with virgil, a 6th-generation 
              San francisco native and a film buff! Ask me questions about films 
              shot in various locations in San Francisco since 1915 till present!🎈\n
              if I get to impress you with my knowledge, tell me "what a good boi!"😸
              """)

        while True:
            if not error_recovery:
                try:
                    user_input = input("You: ")
                    current_user_input = user_input  # Save for potential retries
                except KeyboardInterrupt:
                    print("\nExiting chat session...")
                    break
                except EOFError:  # Handles Ctrl+D
                    print("\nExiting chat session...")
                    break

                # Exit conditions
                if user_input.lower() in terminate_session:
                    print("Exiting chat session...")
                    break

                # Prevent sending empty messages
                if not user_input.strip():
                    continue
            else:
                # We're recovering from an error, use the saved input
                print(f"🙈🙉🙊🐵Retrying previous query: {current_user_input}")
                error_recovery = False  # Reset for next iteration unless we hit another error

            # Send message to Gemini and process any function calls
            try:
                response = chat.send_message(current_user_input)
                retry_count = 0  # Reset on success

                # Main loop for handling responses and function calls
                while response:
                    # log AI response to file for debugging/inspection
                    log_chat_responses_to_file(response)
                    # Check if we have text to display
                    if hasattr(response, 'text') and response.text:
                        # to_user = textwrap.fill(response.text, width=70)
                        print(f"\n _🤖-- : {response.text}\n")
                    
                    # Check for function calls
                    function_call = None
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                function_call = part.function_call
                                break
                    
                    if not function_call:
                        # No function call, we're done with this cycle
                        break
                        
                    # Process the function call using our helper function
                    print(f"Function to call: {function_call.name}")
                    response = process_function_call(function_call, chat)
                    
                    # If process_function_call returns None, exit the loop
                    if not response:
                        break

            except Exception as e:
                if "429 RESOURCE_EXHAUSTED" in str(e) and retry_count < max_retries:
                    retry_count += 1
                    # Extract retry delay if available
                    retry_delay = 6  # Default retry delay in seconds
                    
                    try:
                        retry_info = re.search(r"'retryDelay': '(\d+)s'", str(e))
                        if retry_info:
                            retry_delay = int(retry_info.group(1))
                    except:
                        pass
                    
                    print(f"\n⏳ Rate limit exceeded. Retry {retry_count}/{max_retries}. Waiting {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    
                    # Don't ask for new input, use the same one
                    error_recovery = True
                    continue
                elif retry_count >= max_retries:
                    print(f"\n⚠️ Failed after {max_retries} retries due to rate limits.")
                    print("Consider upgrading your Gemini API plan or implementing longer cooldown periods.")
                    retry_count = 0  # Reset for next interaction
                    error_recovery = False
                else:
                    print(f"\n👎🏽An error occurred: {e}")
                    traceback.print_exc()  # For more detailed error info

    except Exception as e:
        print(f"\nFailed to initialize the chat model or session: {e}")



start_chat_session()


# def start_chat_session():
#     """Starts and manages an interactive chat session with Gemini."""
#     try:
#         # Starting chat client
#         tools = types.Tool(function_declarations=[
#                            convert_to_sqlite_declaration, execute_sql_query_tool])
        
#         config = types.GenerateContentConfig(
#             tools=[tools],
#             # response_mime_type="application/json",
#             system_instruction=system_instruction,
#             temperature=0.1
#         )

#         chat = client.chats.create(
#             model=MODEL_NAME,
#             config=config
#         )

#         print(
#             f"Starting chat with {MODEL_NAME}. Type exit, quit, end, aus or aufhören to end.")
#         print("-" * 30)

#         print("""
#               (●'◡'●): hiya! you are now chatting with virgil, a 6th-generation 
#               San francisco native and a film buff! Ask me questions about films 
#               shot in various locations in San Francisco since 1915 till present!🎈\n
#               if I get to impress you with my knowledge, tell me "what a good boi!"😸
#               """)

#         while True:
#             try:
#                 user_input = input("You: ")
#             except KeyboardInterrupt:
#                 print("\nExiting chat session...")
#                 break
#             except EOFError:  # Handles Ctrl+D
#                 print("\nExiting chat session...")
#                 break

#             # Exit conditions
#             if user_input.lower() in terminate_session:
#                 print("Exiting chat session...")
#                 break

#             # Prevent sending empty messages
#             if not user_input.strip():
#                 continue

#             # Send message to Gemini and process any function calls
#             try:
#                 response = chat.send_message(user_input)

#                 # Main loop for handling responses and function calls
#                 while response:
#                     # log AI response to file for debugging/inspection
#                     log_chat_responses_to_file(response)
#                     # Check if we have text to display
#                     if hasattr(response, 'text') and response.text:
#                         # to_user = textwrap.fill(response.text, width=70)
#                         print(f"\n _🤖-- : {response.text}\n")
                        
                    
#                     # Check for function calls
#                     function_call = None
#                     if response.candidates and response.candidates[0].content.parts:
#                         for part in response.candidates[0].content.parts:
#                             if hasattr(part, 'function_call') and part.function_call:
#                                 function_call = part.function_call
#                                 break
                    
#                     if not function_call:
#                         # No function call, we're done with this cycle
#                         break
                        
#                     # Process the function call using our helper function
#                     print(f"Function to call: {function_call.name}")
#                     response = process_function_call(function_call, chat)
                    
#                     # If process_function_call returns None, exit the loop
#                     if not response:
#                         break

#             except Exception as e:
#                 print(f"\n👎🏽An error occurred: {e}")
#                 traceback.print_exc()  # For more detailed error info

#     except Exception as e:
#         print(f"\nFailed to initialize the chat model or session: {e}")



                # # Process the response
                # if hasattr(response, 'text') and response.text:
                #     print(f"virgil🤖: {response.text}")
                #     continue  # If there's text, just display it and continue

                # # Check for function calls
                # function_call = None
                # if response.candidates and response.candidates[0].content.parts:
                #     for part in response.candidates[0].content.parts:
                #         if hasattr(part, 'function_call') and part.function_call:
                #             function_call = part.function_call
                #             break

                # if not function_call:
                #     print("virgil🤖: (No response or function call provided)")
                #     continue

                # print(f"Function to call: {function_call.name}")

                # response = process_function_call(function_call, chat)

                # Handle the NLP to SQL conversion
                # if function_call.name == "nlp_2_sql_SanFranciscoFilmLocations":
                #     function_args = function_call.args
                #     user_query = function_args.get('natural_language_query')
                #     print(f"Converting query: {user_query}")

                #     # Call your SQL conversion tool
                #     tool_1 = SFMovieQueryProcessor(db_path, user_query)
                #     sql_result = tool_1.analyze()

                #     # Create and send function response
                #     function_response_part = Part.from_function_response(
                #         name="nlp_2_sql_SanFranciscoFilmLocations",
                #         response={"result": sql_result}
                #     )

                #     # Send the result back to continue the conversation
                #     response = chat.send_message(function_response_part)

                #     # Now check if we need to execute an SQL query
                #     if response.candidates and response.candidates[0].content.parts:
                #         for part in response.candidates[0].content.parts:
                #             if hasattr(part, 'function_call') and part.function_call:
                #                 exec_function_call = part.function_call
                #                 if exec_function_call.name == "execute_sql_query":
                #                     sql_query = exec_function_call.args.get(
                #                         "sql_query")
                #                     offset = exec_function_call.args.get(
                #                         "offset", 0)
                #                     limit = exec_function_call.args.get(
                #                         "limit", 5)

                #                     # Execute the SQL query
                #                     print(f"Executing SQL: {sql_query}")
                #                     try:
                #                         # (sql_query: str, offset: int = 0, limit: int = 5)
                #                         sql_exec_result = execute_sql_query(
                #                             sql_query, offset, limit)
                #                         print(
                #                             f"SQL_EXEC_result: {sql_exec_result}")
                #                         # Create and send response
                #                         sql_response_part = Part.from_function_response(
                #                             name="execute_sql_query",
                #                             response=sql_exec_result
                #                         )

                #                         # Send the result back and show the model's interpretation
                #                         final_response = chat.send_message(
                #                             sql_response_part)
                #                         print(f"virgil🤖: {final_response.text}")

                #                     except Exception as e:
                #                         error_msg = f"SQL execution error: {str(e)}"
                #                         print(f"Error: {error_msg}")

                #                         # Inform the model about the error
                #                         error_response_part = Part.from_function_response(
                #                             name="execute_sql_query",
                #                             response={"error": error_msg}
                #                         )
                #                         error_response = chat.send_message(
                #                             error_response_part)
                #                         print(f"virgil🤖: {error_response.text}")
                #                 else:
                #                     # Handle unexpected function call
                #                     print(
                #                         f"Unexpected function call: {exec_function_call.name}")
                #                     print(f"virgil🤖: {response.text}")
                #                 break
                #         else:
                #             # No function call found
                #             print(f"virgil🤖: {response.text}")
                # else:
                #     # Handle direct execute_sql_query or other function calls
                #     print(f"Direct function call: {function_call.name}")
                #     if function_call.name == "execute_sql_query":
                #         # Process direct SQL execution request
                #         sql_query = function_call.args.get("sql_query")
                #         offset = function_call.args.get("offset", 0)
                #         limit = function_call.args.get("limit", 5)

                #         # Execute SQL (same code as above)
                #         sql_exec_result = execute_sql_query(
                #             sql_query, offset, limit)
                #         print(f"🎯🎯DIREKT SQL_EXEC_result: {sql_exec_result}")
                #         # Create and send response
                #         sql_response_part = Part.from_function_response(
                #             name="execute_sql_query",
                #             response=sql_exec_result
                #         )

                #         # Send the result back and show the model's interpretation
                #         final_response = chat.send_message(
                #             sql_response_part)
                #         print(f"virgil🤖: {final_response.text}")

                #     else:
                #         print(f"Unhandled function call: {function_call.name}")



# '''
#  def start_chat_session():
#     """Starts and manages an interactive chat session with Gemini."""
#     try:
#         # Starting chat client
#         tools = types.Tool(function_declarations=[
#                            convert_to_sqlite_declaration, execute_sql_query_tool])
#         config = types.GenerateContentConfig(
#             tools=[tools],
#             system_instruction=system_instruction,
#             temperature=0.1
#         )

#         chat = client.chats.create(
#             model=MODEL_NAME,
#             config=config
#         )

#         print(
#             f"Starting chat with {MODEL_NAME}. Type exit, quit, end, aus or aufhören to end.")
#         print("-" * 30)

#         while True:
#             try:
#                 user_input = input("You: ")
#             except KeyboardInterrupt:
#                 print("\nExiting chat session...")
#                 break
#             except EOFError:  # Handles Ctrl+D
#                 print("\nExiting chat session...")
#                 break

#             # Exit conditions
#             if user_input.lower() in ["exit", "quit", "aus", "end", "aufhören"]:
#                 print("Exiting chat session...")
#                 break

#             # Prevent sending empty messages
#             if not user_input.strip():
#                 continue

#             # Send message to Gemini and handle response (same method)
#             try:
#                 response = chat.send_message(user_input)
#                 print(f"response text part is\n: {response.text}")
#                 print(f"full response is\n: {response}")

#                 if response.candidates[0].content.parts[0].function_call:
#                     function_call = response.candidates[0].content.parts[0].function_call
#                     print(f"Function to call: {function_call.name}")
#                     print("_" * 35)  # Separator for clarity
#                     if function_call.name == "nlp_2_sql_SanFranciscoFilmLocations":
#                         function_args = function_call.args
#                         user_query = function_args.get(
#                             'natural_language_query')
#                         print(f"user message: {user_query}")
#                         print("-" * 35)  # Separator for clarity
#                         #  In your app, you would call your function here:
#                         # user_query = 'what are some movies made in 1920s?'
#                         tool_1 = SFMovieQueryProcessor(db_path, user_query)
#                         result = tool_1.analyze()
#                         print('Ergebniss vom path.py ist\n', result)


#                        # Create the function response part directly
#                         function_response_part = Part.from_function_response(
#                             name="nlp_2_sql_SanFranciscoFilmLocations",
#                             response={
#                                 "result": result
#                             }
#                         )

#                         # Send the function response part to the model
#                         response_2 = chat.send_message(function_response_part)
#                         print(
#                             f"\nGemini Response (after SQL execution tool): {response_2.candidates[0].content.parts[0]}")
#                         # Check if Gemini called the execute_sqlite_query tool
#                         if response_2.candidates[0].content.parts[0].function_call:
#                             function_call_2 = response_2.candidates[0].content.parts[0].function_call
#                             if function_call_2.name == 'execute_sql_query':
#                                 # Simulate the execution of the execute_sqlite_query tool
#                                 # In a real application, you would call your Python function here
#                                 sql_query = function_call_2.args.get(
#                                     "sql_query")
#                                 offset = function_call_2.args.get("offset", 0)
#                                 limit = function_call_2.args.get("limit", 5)
#                                 print(
#                                     f"\nExecuting execute_sqlite_query with query: '{sql_query}', offset: {offset}, limit: {limit}")
#                             else:
#                                 print(
#                                     "Gemini did not call execute_sqlite_query as expected.")
#                         else:
#                             print(
#                                 "Gemini did not call a function after receiving the SQL query.")
#                     else:
#                         print("Gemini did not call nlp_to_sqlite as expected.")
#                 else:
#                     print("No function call found in the response.")

#                  # Use textwrap for potentially long responses
#                 # wrapped_text = textwrap.fill(response.text, width=80)
#                 # print(f"Gemini:\n{wrapped_text}")
#                 # print(response)
#                 # print(response.text)
#                 # print("-" * 30)  # Separator for clarity

#             except Exception as e:
#                 print(f"\nAn error✂️ occurred in 💬: {e}")
#                 print("There might be an issue with the API call or your connection.")
#                 # Optional: break here if you want the chat to end on error
#                 # break

#     except Exception as e:
#         print(f"\n📛Failed📛 to initialize the chat model⚠️ or session⚠️: {e}")
#         print("Please check your API key, model name, and ensure the 'google-genai'📛package is correctly installed.")
# '''


############################# SQL #######################################
# conn = sqlite3.connect(db_path)
# df = pd.read_sql_query(sql_query, conn)

# # Apply pagination
# total_rows = len(df)
# df_paginated = df.iloc[offset:offset+limit]

# # Convert to dict for response
# results = df_paginated.to_dict(orient='records')

# # Create metadata
# metadata = {
#     "total_rows": total_rows,
#     "offset": offset,
#     "limit": limit,
#     "returned_rows": len(results)
# }
############################# SQL #######################################


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
