"""Generic JSON storage operations for all entity types"""

import json
from pathlib import Path
from typing import Dict, Union


def generic_load_json(file_path: Path, key_as_int: bool = False) -> Dict:
    """
    Load JSON data from file

    Args:
        file_path: Path to JSON file
        key_as_int: If True, convert string keys to integers

    Returns:
        Dictionary with loaded data (empty dict if file doesn't exist or is invalid)
    """
    if not file_path.exists():
        return {}

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        if key_as_int:
            return {int(k): v for k, v in data.items()}

        return data

    except (json.JSONDecodeError, ValueError):
        return {}


def generic_save_json(file_path: Path, data: Dict):
    """
    Save data to JSON file

    Args:
        file_path: Path to JSON file
        data: Dictionary to save
    """
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
