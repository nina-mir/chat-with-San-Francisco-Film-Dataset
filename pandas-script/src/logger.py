import json
from pathlib import Path
import jsonlines
from datetime import datetime
from shapely.geometry import Point


def convert_shapely_to_serializable(obj):
    """Recursively convert Shapely objects to serializable format"""
    if isinstance(obj, dict):
        return {key: convert_shapely_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_shapely_to_serializable(item) for item in obj]
    elif isinstance(obj, Point):
        return {
            'type': 'Point',
            'coordinates': [obj.x, obj.y]
        }
    else:
        return obj

def write_to_log_file(message, filename, query=None, jsonlines_flag=False, log_dir="log"):
    """
    Write a message to a log file in the specified directory.
    Creates the directory if it doesn't exist.

    Args:
        message: The content to write
        filename: Name of the log file
        query: Optional ID/query identifier for JSONLines
        jsonlines_flag: If True, write as JSONLines format
        log_dir: Directory to store log files
    """
    try:
        # Simplify path creation - Path.cwd() / log_dir is cleaner
        log_path = Path.cwd() / log_dir
        log_file = log_path / filename

        # Create directory (with parents if needed)
        log_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().isoformat()

        # Write to file
        if jsonlines_flag:
            # Pre-process your message before writing
            processed_message = convert_shapely_to_serializable(message)

            if query is None:
                # Provide a default if query is not specified
                query = "default_id"
            with jsonlines.open(log_file, mode='a') as writer:
                writer.write({
                    'id': query,
                    'timestamp': timestamp,
                    'code_execution_result': processed_message
                })
        else:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(' '*50 + '\n')
                f.write(f"[{timestamp}]")
                f.write(json.dumps(message))
                f.write(' '*50 + '\n')

        print(f"✅😸🐬🐶 Successfully wrote to {log_file}")

    except Exception as e:
        print(f"⚠️⚠️⚠️ Error writing to {filename}: {e}")


# Usage examples:
if __name__ == "__main__":
    # Regular text log
    write_to_log_file("This is a regular log message", "app.log")

    # JSONLines log
    write_to_log_file(
        "Code executed successfully",
        "execution.jsonl",
        query="user_query_123",
        jsonlines_flag=True
    )
