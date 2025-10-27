# src/response_formatter.py
import pandas as pd
import geopandas as gpd
from typing import Dict, Any, Optional
from src.logger import convert_shapely_to_serializable


class ResponseFormatter:
    """
    Converts technical QueryProcessor results into user-friendly chat responses.
    BULLETPROOF VERSION - Shows data no matter what structure it has.
    """

    def __init__(self):
        """Initialize formatter"""
        pass

    def format_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point: format any result type for chat display.
        """
        result_type = result.get('type', 'unknown')

        # Route to appropriate formatter
        if result_type == 'greeting':
            return {'content': result['content'], 'type': 'greeting'}

        elif result_type == 'help':
            return {'content': result['content'], 'type': 'help'}

        elif result_type == 'data_result':
            return self._format_data_result(result)

        elif result_type == 'error':
            return {'content': result['content'], 'type': 'error'}

        else:
            return {'content': result.get('content', 'No response available'), 'type': result_type}

    def _format_data_result(self, result: Dict) -> Dict:
        """
        Format QueryProcessor results - BULLETPROOF version.
        """
        print("\n" + "="*60)
        print("FORMATTER DEBUG")
        print("="*60)
        
        execution_result = result.get('execution_result')
        
        if not execution_result:
            return {
                'content': "Query processed, but no results to display.",
                'type': 'data_result'
            }

        # Extract components
        data = execution_result.get('data')
        summary = execution_result.get('summary', 'Query completed successfully')
        success = execution_result.get('success', True)

        print(f"Summary: {summary}")
        print(f"Data type: {type(data)}")
        print(f"Data (truncated): {str(data)[:500]}")

        # UNWRAP nested structure if present
        if isinstance(data, dict) and 'data' in data:
            inner_data = data.get('data')
            inner_summary = data.get('summary')
            
            if inner_summary and inner_summary != summary:
                summary = inner_summary
            
            data = inner_data
            print(f"UNWRAPPED - New data type: {type(data)}")
            print(f"UNWRAPPED - New data: {str(data)[:500]}")

        # Handle failure
        if not success:
            error_msg = execution_result.get('metadata', {}).get('error', 'Unknown error')
            return {'content': f"Query failed: {error_msg}", 'type': 'error'}

        # Build response
        response = {
            'type': 'data_result',
            'content': f"**{summary}**\n\n"
        }

        # SIMPLE DECISION TREE - No fancy logic
        
        # 1. DataFrame/GeoDataFrame → Show as table
        if isinstance(data, (pd.DataFrame, gpd.GeoDataFrame)):
            print("✓ Detected: DataFrame")
            if not data.empty:
                response['content'] += f"Found **{len(data)} result(s)**\n\n_See table below_"
                response['dataframe'] = data
            else:
                response['content'] += "_No data in DataFrame_"
        
        # 2. List of dicts → Always convert to DataFrame
        elif isinstance(data, (list, tuple)) and data and isinstance(data[0], dict):
            print("✓ Detected: List of dicts")
            df = pd.DataFrame(data)
            response['content'] += f"Found **{len(df)} result(s)**\n\n_See table below_"
            response['dataframe'] = df
        
        # 3. Simple list (strings, numbers) → Convert to DataFrame
        elif isinstance(data, (list, tuple)) and data:
            print("✓ Detected: Simple list")
            # Check what type of items
            first_item = data[0]
            if isinstance(first_item, (str, int, float)):
                df = pd.DataFrame(data, columns=['Result'])
                response['content'] += f"Found **{len(df)} result(s)**\n\n_See table below_"
                response['dataframe'] = df
            else:
                # Complex items, show as text
                response['content'] += self._format_list_as_text(data)
        
        # 4. Dict with lists → Find the first list and show it
        elif isinstance(data, dict):
            print("✓ Detected: Dict")
            list_found = False
            
            # Look for ANY list in the dict
            for key, value in data.items():
                if isinstance(value, list) and value:
                    print(f"  Found list in key: {key}, length: {len(value)}")
                    
                    # Check if it's a list of simple values
                    first_val = value[0] if value else None
                    
                    if isinstance(first_val, (str, int, float)):
                        # Simple list → DataFrame
                        column_name = key.replace('_', ' ').title()
                        df = pd.DataFrame(value, columns=[column_name])
                        response['content'] += f"Found **{len(df)} result(s)**\n\n_See table below_"
                        response['dataframe'] = df
                        list_found = True
                        break
                    elif isinstance(first_val, dict):
                        # List of dicts → DataFrame
                        df = pd.DataFrame(value)
                        response['content'] += f"Found **{len(df)} result(s)**\n\n_See table below_"
                        response['dataframe'] = df
                        list_found = True
                        break
            
            if not list_found:
                # No list found, show dict as key-value table
                print("  No list found in dict, showing as key-value")
                if len(data) <= 50:
                    df = pd.DataFrame(list(data.items()), columns=['Key', 'Value'])
                    response['content'] += f"Found **{len(df)} result(s)**\n\n_See table below_"
                    response['dataframe'] = df
                else:
                    response['content'] += self._format_dict_as_text(data)
        
        # 5. Simple value (int, float, str)
        elif isinstance(data, (int, float)):
            print("✓ Detected: Number")
            response['content'] += f"**Result:** {data}"
        
        elif isinstance(data, str):
            print("✓ Detected: String")
            response['content'] += data
        
        # 6. None or empty
        elif data is None:
            print("✓ Detected: None")
            response['content'] += "_No data returned_"
        
        # 7. Fallback - serialize it
        else:
            print(f"✓ Detected: Other ({type(data)})")
            serialized = convert_shapely_to_serializable(data)
            response['content'] += f"```json\n{str(serialized)[:1000]}\n```"

        # Add map if available
        if result.get('map_html'):
            response['map_html'] = result['map_html']
            response['content'] += "\n\n**Map displayed below**"

        print(f"\nFinal response has dataframe: {'dataframe' in response}")
        if 'dataframe' in response:
            print(f"DataFrame shape: {response['dataframe'].shape}")
            print(f"DataFrame columns: {list(response['dataframe'].columns)}")
            print(f"DataFrame head:\n{response['dataframe'].head()}")
        print("="*60 + "\n")

        return response

    def _format_list_as_text(self, data: list) -> str:
        """Format list as bullet points"""
        count = len(data)
        if count <= 10:
            items = "\n".join([f"• {item}" for item in data])
            return f"Found **{count} item(s):**\n\n{items}"
        else:
            preview = "\n".join([f"• {item}" for item in data[:10]])
            return f"Found **{count} items** (showing first 10):\n\n{preview}\n\n_...and {count - 10} more_"

    def _format_dict_as_text(self, data: dict) -> str:
        """Format dict as key-value pairs"""
        if not data:
            return "_Empty result_"
        
        formatted = ""
        for key, value in list(data.items())[:20]:
            if isinstance(value, list):
                formatted += f"**{key}:** {len(value)} items\n"
            else:
                formatted += f"**{key}:** {value}\n"
        
        if len(data) > 20:
            formatted += f"\n_...and {len(data) - 20} more entries_"
        
        return formatted