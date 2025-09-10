"""
Code Executor Module
Handles safe execution of dynamically generated GeoPandas code with proper
namespace setup, error handling, and result formatting.
"""

import traceback
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from typing import Dict, Any, Optional, Callable


class CodeExecutor:
    """
    Executes dynamically generated GeoPandas code in a controlled environment.
    Provides namespace setup, execution monitoring, and standardized result formatting.
    """
    
    def __init__(self, gdf: gpd.GeoDataFrame):
        """
        Initialize the CodeExecutor with the target GeoDataFrame.
        
        Args:
            gdf: The GeoPandas dataframe to operate on
        """
        self.gdf = gdf
        self.base_namespace = self._setup_base_namespace()
    
    def _setup_base_namespace(self) -> Dict[str, Any]:
        """
        Set up the base namespace with required libraries and data.
        
        Returns:
            Dictionary containing the execution namespace
        """
        return {
            "gdf": self.gdf,
            "pd": pd,
            "gpd": gpd,
            "np": np,
            "Point": Point,
            "result": None
        }
    
    def _prepare_code(self, code: str, function_name: str = "process_sf_film_query") -> str:
        """
        Prepare the code for execution by adding the function call.
        
        Args:
            code: The Python code to execute
            function_name: Name of the main function to call
            
        Returns:
            Complete code ready for execution
        """
        # Ensure the code doesn't already contain the function call
        if f"result = {function_name}(gdf)" in code:
            return code
            
        return f"""{code}

# Execute the main function
result = {function_name}(gdf)
"""
    
    def execute_code(
        self, 
        code: str, 
        function_name: str = "process_sf_film_query",
        custom_namespace: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the provided code and return formatted results.
        
        Args:
            code: The Python code to execute
            function_name: Name of the main function to call
            custom_namespace: Additional variables to add to the namespace
            
        Returns:
            Dictionary containing execution results and metadata
        """
        # Create execution namespace
        namespace = self.base_namespace.copy()
        if custom_namespace:
            namespace.update(custom_namespace)
        
        try:
            # Prepare the complete code
            full_code = self._prepare_code(code, function_name)
            
            # Execute the code
            exec(full_code, namespace)
            
            # Extract and format the result
            return self._format_success_result(namespace.get('result'))
            
        except Exception as e:
            return self._format_error_result(e)
    
    def _format_success_result(self, result: Any) -> Dict[str, Any]:
        """
        Format a successful execution result.
        
        Args:
            result: The result returned by the executed code
            
        Returns:
            Formatted result dictionary
        """
        if result is None:
            return {
                "success": True,
                "data": None,
                "summary": "Execution completed but no result was returned",
                "metadata": {
                    "result_type": "none",
                    "execution_status": "completed"
                }
            }
        
        # Determine result type and format accordingly
        result_type = self._determine_result_type(result)
        
        return {
            "success": True,
            "data": result,
            "summary": self._generate_summary(result, result_type),
            "metadata": {
                "result_type": result_type,
                "execution_status": "completed",
                **self._extract_metadata(result, result_type)
            }
        }
    
    def _format_error_result(self, error: Exception) -> Dict[str, Any]:
        """
        Format an error result with detailed information.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Formatted error result dictionary
        """
        return {
            "success": False,
            "data": None,
            "summary": f"Error executing generated code: {str(error)}",
            "metadata": {
                "error": str(error),
                "error_type": type(error).__name__,
                "traceback": traceback.format_exc(),
                "execution_status": "failed"
            }
        }
    
    def _determine_result_type(self, result: Any) -> str:
        """
        Determine the type of result returned.
        
        Args:
            result: The result to analyze
            
        Returns:
            String describing the result type
        """
        if isinstance(result, dict):
            return "dictionary"
        elif isinstance(result, (pd.DataFrame, gpd.GeoDataFrame)):
            return "dataframe"
        elif isinstance(result, (list, tuple)):
            return "collection"
        elif isinstance(result, (int, float)):
            return "numeric"
        elif isinstance(result, str):
            return "string"
        else:
            return "other"
    
    def _generate_summary(self, result: Any, result_type: str) -> str:
        """
        Generate a human-readable summary of the result.
        
        Args:
            result: The result to summarize
            result_type: The type of result
            
        Returns:
            Summary string
        """
        if result_type == "dataframe":
            rows, cols = result.shape
            return f"Returned {rows} rows and {cols} columns"
        elif result_type == "collection":
            return f"Returned {len(result)} items"
        elif result_type == "numeric":
            return f"Returned numeric value: {result}"
        elif result_type == "string":
            return f"Returned text result"
        elif result_type == "dictionary":
            return f"Returned dictionary with {len(result)} keys"
        else:
            return "Execution completed successfully"
    
    def _extract_metadata(self, result: Any, result_type: str) -> Dict[str, Any]:
        """
        Extract additional metadata from the result.
        
        Args:
            result: The result to analyze
            result_type: The type of result
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        if result_type == "dataframe":
            metadata.update({
                "shape": result.shape,
                "columns": list(result.columns) if hasattr(result, 'columns') else None,
                "is_geodataframe": isinstance(result, gpd.GeoDataFrame)
            })
        elif result_type == "collection":
            metadata["length"] = len(result)
        elif result_type == "dictionary":
            metadata["keys"] = list(result.keys())
            
        return metadata
    
    def validate_code(self, code: str) -> Dict[str, Any]:
        """
        Perform basic validation on code before execution.
        
        Args:
            code: The code to validate
            
        Returns:
            Validation result dictionary
        """
        issues = []
        
        # Check for potentially dangerous operations
        dangerous_patterns = [
            'import os',
            'import sys',
            'import subprocess',
            'exec(',
            'eval(',
            # 'open(',
            '__import__',
            'globals()',
            'locals()'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code:
                issues.append(f"Potentially unsafe operation detected: {pattern}")
        
        # Check for required function
        if 'def process_sf_film_query(' not in code:
            issues.append("Required function 'process_sf_film_query' not found")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "code_length": len(code)
        }
    
    def execute_with_validation(self, code: str, **kwargs) -> Dict[str, Any]:
        """
        Execute code with pre-execution validation.
        
        Args:
            code: The code to execute
            **kwargs: Additional arguments for execute_code
            
        Returns:
            Execution result with validation information
        """
        # Validate first
        validation_result = self.validate_code(code)
        
        if not validation_result["is_valid"]:
            return {
                "success": False,
                "data": None,
                "summary": "Code validation failed",
                "metadata": {
                    "validation": validation_result,
                    "execution_status": "validation_failed"
                }
            }
        
        # Execute if validation passes
        result = self.execute_code(code, **kwargs)
        result["metadata"]["validation"] = validation_result
        
        return result


# Usage example functions
def example_usage():
    """
    Demonstrate how to use the CodeExecutor class.
    This is just for illustration - actual usage would depend on your data.
    """
    # Example 1: Basic usage
    # Assume you have a GeoDataFrame loaded
    # gdf = your_geodataframe_here
    # executor = CodeExecutor(gdf)
    
    # Example generated code
    sample_code = '''
def process_sf_film_query(gdf):
    # Filter for films with "matrix" in title
    filtered = gdf[gdf['Title'].str.contains('Matrix', case=False, na=False)]
    return {
        "data": filtered,
        "summary": f"Found {len(filtered)} films with 'Matrix' in title",
        "metadata": {"count": len(filtered)}
    }
    '''
    
    # Execute the code
    # result = executor.execute_code(sample_code)
    # print("Execution Result:", result)
    
    # Example 2: With validation
    # result = executor.execute_with_validation(sample_code)
    # print("Validated Execution:", result)
    
    # Example 3: Custom namespace
    # custom_vars = {"search_term": "matrix"}
    # result = executor.execute_code(sample_code, custom_namespace=custom_vars)
    
    pass


def integration_example():
    """
    Show how to integrate CodeExecutor with the QueryProcessor.
    """
    # In your QueryProcessor.__init__():
    # self.code_executor = CodeExecutor(self.gdf)
    
    # Replace the execute_generated_code method with:
    # def execute_generated_code(self, code: str):
    #     return self.code_executor.execute_with_validation(code)
    
    pass