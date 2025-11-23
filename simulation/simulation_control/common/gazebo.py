"""Generic Gazebo model discovery operations"""

import re
import subprocess
from pathlib import Path
from typing import Callable, Dict

from .storage import generic_load_json, generic_save_json


def generic_discover_from_gazebo(
    pattern: str,
    entity_type: str,
    storage_file: Path,
    id_generator: Callable[[str], tuple]
) -> Dict:
    """
    Query Gazebo to discover active models and merge with JSON metadata

    Args:
        pattern: Regex pattern to match models (e.g., r'x500_(\d+)', r'zone_\w+')
        entity_type: Type name for logging (e.g., "drone", "zone")
        storage_file: Path to JSON storage file
        id_generator: Function that takes a regex match and returns (entity_key, metadata_dict)

    Returns:
        Dict of discovered entities merged with existing JSON metadata
    """
    discovered = {}

    try:
        # Query Gazebo for all models
        result = subprocess.run(
            ["gz", "model", "--list"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # Parse output to find matching models
            regex_pattern = re.compile(f'^\\s*-\\s*{pattern}$', re.MULTILINE)
            matches = regex_pattern.findall(result.stdout)

            for match in matches:
                entity_key, metadata = id_generator(match)
                discovered[entity_key] = metadata

        else:
            print(f"Warning: gz model --list failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("Warning: gz model --list timeout")
    except Exception as e:
        print(f"Warning: Gazebo {entity_type} discovery failed: {e}")

    # Load existing metadata from JSON
    existing = generic_load_json(storage_file)

    # Merge: keep metadata from JSON for entities that exist in Gazebo
    merged = {}
    for entity_key, gazebo_data in discovered.items():
        if entity_key in existing:
            # Entity exists in both - use JSON metadata (more complete)
            merged[entity_key] = existing[entity_key]
        else:
            # Entity only in Gazebo - use discovered data
            merged[entity_key] = gazebo_data

    # Sync JSON with Gazebo reality (remove ghost entries)
    if merged != existing:
        generic_save_json(storage_file, merged)
        print(f"Synchronized {storage_file.name} with Gazebo (removed {len(existing) - len(merged)} ghost entries)")

    return merged
