###############################################
# LIBRARY IMPORTS
###############################################
import os
import sqlite3
import pandas as pd
import json
import dataclasses
import typing_extensions as typing
from pathlib import Path

###############################################
# PATH to SQLite database
###############################################
DB_FILE = 'sf-films-geocode.db'
db_path = Path.cwd().joinpath("..").joinpath(DB_FILE).resolve()
###############################################


def execute_sql_query(sql_query: str, offset: int = 0, limit: int = 5) -> dict:
    """
    Executes a SQL query against a SQLite DB with pagination.

    Args:
        sql_query: The SQL query to execute.
        offset: The starting row number (0-based index) for pagination. Defaults to 0.
        limit: The maximum number of rows to return per page. Defaults to 5.

    Returns:
        A dictionary containing the following keys:
            rows: A list of tuples representing the fetched rows.
            total_results: The total number of rows matching the query.
            offset: The current offset used for pagination.
            limit: The current limit used for pagination.
            next_offset: The offset for the next page, or None if there are no more pages.
            remaining: The number of remaining results after the current page.
    """     
    try:
        conn = sqlite3.connect(db_file=db_path)
        cursor = conn.cursor()

        # Count total results
        count_query = f"SELECT COUNT(*) FROM ({sql_query}) AS subquery"
        cursor.execute(count_query)
        total_results = cursor.fetchone()[0]

        # Fetch paginated chunk
        paginated_sql = f"{sql_query.strip().rstrip(';')} LIMIT {limit} OFFSET {offset}"
        cursor.execute(paginated_sql)
        rows = cursor.fetchall()

        conn.close()

        return {
            "rows": rows,
            "total_results": total_results,
            "offset": offset,
            "limit": limit,
            "next_offset": offset + limit if (offset + limit) < total_results else None,
            "remaining": max(total_results - (offset + limit), 0)
        }

    except Exception as e:
        raise Exception(f"Error executing SQLite query: {str(e)}")
    finally:
        conn.close()







# result = pd.read_sql_query(sql_query, conn)
            # Store the full results for potential follow-up queries
            # self.last_full_results = result
            # return result

'''
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

'''