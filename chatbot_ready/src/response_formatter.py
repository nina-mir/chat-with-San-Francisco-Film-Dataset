# src/response_formatter.py
import pandas as pd
import geopandas as gpd
from typing import Dict, Any, Optional
from src.logger import convert_shapely_to_serializable


class ResponseFormatter:
    """
    Converts technical QueryProcessor results into user-friendly chat responses.
    Handles dataframes, maps, errors, and various result types.
    """

    def __init__(self):
        """Initialize formatter"""
        pass

    def format_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point: format any result type for chat display.

        Args:
            result: Output from ChatbotCoordinator

        Returns:
            Dict with 'content' (markdown text) and optional components (map, dataframe)
        """
        result_type = result.get('type', 'unknown')

        # Route to appropriate formatter
        if result_type == 'greeting':
            return self._format_greeting(result)

        elif result_type == 'help':
            return self._format_help(result)

        elif result_type == 'data_result':
            return self._format_data_result(result)

        elif result_type == 'error':
            return self._format_error(result)

        else:
            # Fallback
            return {
                'content': result.get('content', 'No response available'),
                'type': result_type
            }

    def _format_greeting(self, result: Dict) -> Dict:
        """Format greeting messages (pass through)"""
        return {
            'content': result['content'],
            'type': 'greeting'
        }

    def _format_help(self, result: Dict) -> Dict:
        """Format help messages (pass through)"""
        return {
            'content': result['content'],
            'type': 'help'
        }

    def _format_error(self, result: Dict) -> Dict:
        """Format error messages"""
        return {
            'content': result['content'],
            'type': 'error'
        }

    def _format_data_result(self, result: Dict) -> Dict:
        """
        Format QueryProcessor results.
        This is where the magic happens!
        """
        # 🔍 FULL DEBUG DUMP
        # print("\n" + "="*60)
        # print("🔍 FORMATTER DEBUG - Full Result Object")
        # print("="*60)
        # print(f"Result keys: {result.keys()}")
        # print(f"Result type field: {result.get('type')}")
        # print(f"Has 'execution_result': {'execution_result' in result}")
        # print(f"Has 'query_result': {'query_result' in result}")

        # Print full result structure (first 500 chars)
        import json
        
        try:
            result_str = json.dumps(result, default=str, indent=2)
            print(f"Full result (truncated):\n{result_str[:1000]}")
        except:
            print(f"Result: {str(result)[:1000]}")

        print("="*60 + "\n")

        execution_result = result.get('execution_result')

        print(f"🔍 execution_result: {execution_result}")
        print(f"🔍 execution_result type: {type(execution_result)}")

        if not execution_result:
            print("❌ PROBLEM: execution_result is None or missing!")
            return {
                'content': "✅ Query processed, but no results to display.",
                'type': 'data_result'
            }

        execution_result = result.get('execution_result')

        if not execution_result:
            return {
                'content': "✅ Query processed, but no results to display.",
                'type': 'data_result'
            }

        # Extract components
        data = execution_result.get('data')
        summary = execution_result.get(
            'summary', 'Query completed successfully')
        success = execution_result.get('success', True)

        # 🔧 UNWRAP NESTED STRUCTURE (do this ONCE at the top)
        # Your QueryProcessor returns: {data: {data: [...], summary: '...', metadata: {...}}}
        # We need to extract the inner structure
        if isinstance(data, dict) and 'data' in data:
            # This is the nested structure from your code_executor
            inner_data = data.get('data')
            inner_summary = data.get('summary')
            inner_metadata = data.get('metadata', {})

            # Use inner summary if it's more descriptive
            if inner_summary and inner_summary != summary:
                summary = inner_summary

            # Replace data with actual data
            data = inner_data

            print(f"🔍 UNWRAPPED: data type is now: {type(data)}")

        # Handle failure
        if not success:
            error_msg = execution_result.get(
                'metadata', {}).get('error', 'Unknown error')
            return {
                'content': f"⚠️ Query failed: {error_msg}",
                'type': 'error'
            }

        # Build response
        response = {
            'type': 'data_result',
            'content': f"✅ **{summary}**\n\n"
        }

        # Now data is unwrapped, so all these methods work correctly!
        if data is None:
            response['content'] += "_No data returned._"

        elif isinstance(data, (pd.DataFrame, gpd.GeoDataFrame)):
            response['content'] += self._format_dataframe_summary(data)
            response['dataframe'] = data

        elif isinstance(data, dict):
            # Convert dict to DataFrame for better display if it's simple key-value pairs
            if data and all(isinstance(v, (int, float, str)) for v in list(data.values())[:5]):
                # Looks like a simple dict - convert to DataFrame
                
                # Create DataFrame from dict
                df = pd.DataFrame(list(data.items()), columns=['Key', 'Value'])
                
                response['content'] += f"Found **{len(df)} entries**:\n\n_See table below_"
                response['dataframe'] = df
            else:
                # Complex dict, use text formatting
                response['content'] += self._format_dict_data(data)

        elif isinstance(data, (list, tuple)):
            # ✅ FIXED: Check if it's structured data (list of dicts) FIRST
            if data and isinstance(data[0], dict):
                # This is structured data - ALWAYS use a table regardless of length!
                df = pd.DataFrame(data)
                
                if len(data) > 10:
                    response['content'] += f"Found **{len(data)} items**\n\n_Full results in table below ⬇️_"
                else:
                    response['content'] += f"_Full results in table below ⬇️_"
                
                response['dataframe'] = df
            
            elif len(data) > 10:
                # Simple list with many items - use table
                df = pd.DataFrame(data, columns=['Result'])
                response['content'] += f"Found **{len(data)} items**\n\n_Full results in table below ⬇️_"
                response['dataframe'] = df
            else:
                # Short simple list (not structured data) - show inline
                response['content'] += self._format_list_data(data)

        elif isinstance(data, (int, float)):
            response['content'] += f"**Result:** {data}"

        elif isinstance(data, str):
            response['content'] += data

        else:
            # Fallback: use your serializer!
            serialized = convert_shapely_to_serializable(data)
            response['content'] += f"```\n{serialized}\n```"

        # Add map if available
        if result.get('map_html'):
            response['map_html'] = result['map_html']
            response['content'] += "\n\n📍 **Map displayed below**"

        return response

    def _format_dataframe_summary(self, df: pd.DataFrame) -> str:
        """Create a friendly summary of dataframe contents"""
        rows, cols = df.shape

        summary = f"Found **{rows} result{'s' if rows != 1 else ''}** "

        # Mention key columns if small dataframe
        if rows <= 10:
            summary += "\n\n_See full details in the table below._"
        else:
            summary += f"\n\n_Showing first 10 of {rows} results in table below._"

        return summary

    def _format_dict_data(self, data: dict) -> str:
        """Format dictionary data for display"""
        if not data:
            return "_Empty result_"

        # Check if it's a simple key-value dict
        if len(data) <= 20:
            formatted = ""
            for key, value in data.items():
                # Handle different value types
                if isinstance(value, list):
                    formatted += f"**{key}:** {len(value)} items\n"
                elif isinstance(value, (int, float)):
                    formatted += f"**{key}:** {value}\n"
                else:
                    formatted += f"**{key}:** {value}\n"
            return formatted
        else:
            # Too large, show summary
            return f"_Result contains {len(data)} entries. See details below._"

    def _format_list_data(self, data: list) -> str:
        """Format list data for display"""
        if not data:
            return "_Empty list_"

        count = len(data)

        # Show first few items
        if count <= 10:
            items = "\n".join([f"• {item}" for item in data])
            return f"Found **{count} item{'s' if count != 1 else ''}:**\n\n{items}"
        else:
            # Show preview
            preview = "\n".join([f"• {item}" for item in data[:10]])
            return f"Found **{count} items** (showing first 10):\n\n{preview}\n\n_...and {count - 10} more_"


# Optional: Add specialized formatters for specific query types
class QueryTypeDetector:
    """
    Detect what kind of query was asked to customize formatting.
    (Optional - use if enough time to spend on this!)
    """

    @staticmethod
    def detect_query_type(query: str) -> str:
        """Detect query category for specialized formatting"""
        query_lower = query.lower()

        if 'how many' in query_lower or 'count' in query_lower:
            return 'count'

        elif 'top' in query_lower or 'most' in query_lower or 'least' in query_lower:
            return 'ranking'

        elif 'where' in query_lower or 'location' in query_lower:
            return 'spatial'

        elif 'list' in query_lower or 'show' in query_lower:
            return 'list'

        else:
            return 'general'