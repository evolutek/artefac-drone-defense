#!/usr/bin/env python3
"""
Convert 16-bit grayscale heightmap to format compatible with Cesium.js CustomHeightmapTerrainProvider.

Cesium expects a 2D array of height values in meters.
We'll export this as a simple JSON file with metadata for easy loading in JavaScript.

Input: Heightmap.png (513x513, 16-bit grayscale)
Output: heightmap_data.json (height values + metadata)
"""

import numpy as np
from PIL import Image
import json
import os

# Configuration
INPUT_HEIGHTMAP = "/home/lecrabe/dev/evolutek/artefac-drone-defense/simulation/models/Harmonic Terrain/materials/textures/Heightmap.png"
OUTPUT_JSON = "/home/lecrabe/dev/evolutek/artefac-drone-defense/frontend/public/terrain/heightmap_data.json"
MAX_HEIGHT_METERS = 201.66  # From model.sdf

def convert_heightmap_to_cesium():
    """Convert 16-bit heightmap to Cesium-compatible JSON format."""
    print(f"🗺️  Converting heightmap to Cesium format...")
    print(f"Input: {INPUT_HEIGHTMAP}")
    print(f"Output: {OUTPUT_JSON}")

    # Load 16-bit heightmap
    heightmap = Image.open(INPUT_HEIGHTMAP)
    height_array = np.array(heightmap, dtype=np.float32)

    print(f"Heightmap size: {height_array.shape}")
    print(f"Value range: {height_array.min():.0f} - {height_array.max():.0f} (16-bit)")

    # Normalize to meters (0-65535 → 0-MAX_HEIGHT_METERS)
    height_meters = (height_array / 65535.0) * MAX_HEIGHT_METERS

    print(f"Height in meters: {height_meters.min():.2f}m - {height_meters.max():.2f}m")
    print(f"Relief: {height_meters.max() - height_meters.min():.2f}m")

    # Prepare data structure for Cesium
    # Cesium expects heights in row-major order (north to south, west to east)
    data = {
        "width": int(height_array.shape[1]),
        "height": int(height_array.shape[0]),
        "minHeight": float(height_meters.min()),
        "maxHeight": float(height_meters.max()),
        "heights": height_meters.flatten().tolist()  # Flatten to 1D array
    }

    # Save as JSON
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(data, f)

    print(f"✅ Cesium heightmap data saved: {OUTPUT_JSON}")
    print(f"Size: {height_array.shape}")
    print(f"Total data points: {len(data['heights'])}")

    # Calculate file size
    file_size = os.path.getsize(OUTPUT_JSON) / 1024 / 1024
    print(f"File size: {file_size:.2f} MB")

    # Statistics
    print(f"\n📊 Terrain Statistics:")
    print(f"  Min altitude: {height_meters.min():.2f}m")
    print(f"  Max altitude: {height_meters.max():.2f}m")
    print(f"  Avg altitude: {height_meters.mean():.2f}m")
    print(f"  Relief: {height_meters.max() - height_meters.min():.2f}m")


if __name__ == "__main__":
    convert_heightmap_to_cesium()
