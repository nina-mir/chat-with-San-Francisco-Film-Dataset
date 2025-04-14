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