from google import genai
from google.genai import types
from typing import Any


# Import API key and model name configuration
from src import config # The refactoring suggestions indicate reliance on config.GEMINI_API_KEY and config.MODEL_NAME

class GenerativeAIService:
    """
    Encapsulates all direct interactions with the generative AI model.
    Handles client instantiation, content generation calls, and API-specific error handling.
    """

    def __init__(self):
        """
        Initializes the GenerativeAIService by loading API configuration
        and setting up the generative AI client.
        """
        # Load GEMINI_API_KEY from config
        self.api_key: str = config.GEMINI_API_KEY

        # Load MODEL_NAME from config
        self.model_name: str = config.MODEL_NAME

        # Ensure API key is present before proceeding
        if not self.api_key:
            # Replicate the initial error check for the API key [3]
            raise RuntimeError(
                "GEMINI_API_KEY not found. "
                "Please ensure you have a .env file in the same directory "
                "with the line: GEMINI_API_KEY='YOUR_API_KEY'"
            )

        # Initialize the generative AI client using the API key
        self.client = genai.Client(api_key=self.api_key)

    def generate_content(self, system_instructions: str, user_query: str, temperature: int = 0) -> Any:
        """
        Calls the generative AI API to generate content based on system instructions and a user query.

        This method encapsulates the logic previously found in the QueryProcessor's
        _call_generative_api method [2].

        Args:
            system_instructions: The detailed system instructions for the AI model.
            user_query: The natural language user query or input to be processed .

        Returns:
            The raw API response object from the generative AI model [2].

        Raises:
            RuntimeError: If the API call fails for any reason [1, 7].
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name, # Uses the configured model name 
                contents=user_query, # Passes the user's query as content
                config=types.GenerateContentConfig(
                    system_instruction=system_instructions, # Applies specific system instructions
                    response_mime_type="application/json", # Requests JSON output 
                    temperature=temperature, # Sets the creativity level of the response
                ),
            )
            return response
        except Exception as e:
            # Handles API-specific errors, as suggested for this module
            # This replicates the error handling from the original _call_generative_api
            raise RuntimeError(f"API call failed: {str(e)}")