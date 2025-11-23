#!/usr/bin/env python3
"""
Convert 16-bit grayscale heightmap to colored topographic map and terrain-rgb DEM.

Input: Heightmap.png (513x513, 16-bit grayscale)
Outputs:
  - topographic_map.png (RGB colorized for 2D display)
  - terrain_rgb.png (Mapbox terrain-rgb encoded DEM for 3D terrain)

Terrain-RGB encoding:
  height = -10000 + ((R * 256 * 256 + G * 256 + B) * 0.1)
"""

import numpy as np
from PIL import Image
import os

# Configuration
INPUT_HEIGHTMAP = "/home/lecrabe/dev/evolutek/artefac-drone-defense/simulation/models/Harmonic Terrain/materials/textures/Heightmap.png"
OUTPUT_TOPO = "/home/lecrabe/dev/evolutek/artefac-drone-defense/frontend/public/terrain/topographic_map.png"
OUTPUT_DEM = "/home/lecrabe/dev/evolutek/artefac-drone-defense/frontend/public/terrain/terrain_rgb.png"
MAX_HEIGHT_METERS = 201.66  # From model.sdf

# Topographic color gradient (normalized 0-1)
# Format: [(altitude_fraction, (R, G, B))]
COLOR_STOPS = [
    (0.0, (34, 102, 51)),      # Dark green (low valleys)
    (0.2, (102, 153, 51)),     # Light green (plains)
    (0.4, (204, 204, 102)),    # Yellow (hills)
    (0.6, (153, 102, 51)),     # Brown (mountains)
    (0.8, (204, 153, 102)),    # Light brown (high peaks)
    (1.0, (255, 255, 255)),    # White (snow caps)
]


def interpolate_color(value, stops):
    """Interpolate RGB color from gradient stops."""
    value = np.clip(value, 0.0, 1.0)

    for i in range(len(stops) - 1):
        low_stop, low_color = stops[i]
        high_stop, high_color = stops[i + 1]

        if low_stop <= value <= high_stop:
            # Linear interpolation between two stops
            t = (value - low_stop) / (high_stop - low_stop)
            r = int(low_color[0] + t * (high_color[0] - low_color[0]))
            g = int(low_color[1] + t * (high_color[1] - low_color[1]))
            b = int(low_color[2] + t * (high_color[2] - low_color[2]))
            return (r, g, b)

    return stops[-1][1]  # Return highest color if above range


def convert_heightmap_to_topographic():
    """Convert 16-bit heightmap to colorized topographic map."""
    print(f"🗺️  Converting heightmap to topographic map...")
    print(f"Input: {INPUT_HEIGHTMAP}")
    print(f"Output: {OUTPUT_TOPO}")

    # Load 16-bit heightmap
    heightmap = Image.open(INPUT_HEIGHTMAP)
    height_array = np.array(heightmap, dtype=np.float32)

    print(f"Heightmap size: {height_array.shape}")
    print(f"Value range: {height_array.min():.0f} - {height_array.max():.0f} (16-bit)")

    # Normalize to 0-1 (16-bit range is 0-65535)
    normalized = height_array / 65535.0

    print(f"Normalized range: {normalized.min():.3f} - {normalized.max():.3f}")

    # Create RGB output
    height, width = normalized.shape
    rgb_array = np.zeros((height, width, 3), dtype=np.uint8)

    # Apply color gradient
    print("Applying topographic color gradient...")
    for y in range(height):
        for x in range(width):
            altitude_fraction = normalized[y, x]
            rgb_array[y, x] = interpolate_color(altitude_fraction, COLOR_STOPS)

    # Save output
    os.makedirs(os.path.dirname(OUTPUT_TOPO), exist_ok=True)
    output_image = Image.fromarray(rgb_array, mode='RGB')
    output_image.save(OUTPUT_TOPO, 'PNG', optimize=True)

    print(f"✅ Topographic map saved: {OUTPUT_TOPO}")
    print(f"Size: {output_image.size}")

    # Calculate statistics
    avg_altitude = normalized.mean() * MAX_HEIGHT_METERS
    max_altitude = normalized.max() * MAX_HEIGHT_METERS
    min_altitude = normalized.min() * MAX_HEIGHT_METERS

    print(f"\n📊 Terrain Statistics:")
    print(f"  Min altitude: {min_altitude:.2f}m")
    print(f"  Max altitude: {max_altitude:.2f}m")
    print(f"  Avg altitude: {avg_altitude:.2f}m")
    print(f"  Relief: {max_altitude - min_altitude:.2f}m")


def convert_heightmap_to_terrain_rgb():
    """Convert 16-bit heightmap to Mapbox terrain-rgb format for 3D terrain."""
    print(f"\n🏔️  Converting heightmap to terrain-rgb DEM...")
    print(f"Input: {INPUT_HEIGHTMAP}")
    print(f"Output: {OUTPUT_DEM}")

    # Load 16-bit heightmap
    heightmap = Image.open(INPUT_HEIGHTMAP)
    height_array = np.array(heightmap, dtype=np.float32)

    # Normalize to 0-1 then scale to meters
    normalized = height_array / 65535.0
    height_meters = normalized * MAX_HEIGHT_METERS

    print(f"Height range: {height_meters.min():.2f}m - {height_meters.max():.2f}m")

    # Mapbox terrain-rgb encoding: height = -10000 + ((R * 256² + G * 256 + B) * 0.1)
    # Rearranged: (height + 10000) / 0.1 = R * 256² + G * 256 + B
    encoded_height = ((height_meters + 10000) / 0.1).astype(np.uint32)

    # Extract RGB channels
    R = (encoded_height // (256 * 256)) % 256
    G = (encoded_height // 256) % 256
    B = encoded_height % 256

    # Stack into RGB image
    height, width = height_array.shape
    rgb_array = np.zeros((height, width, 3), dtype=np.uint8)
    rgb_array[:, :, 0] = R
    rgb_array[:, :, 1] = G
    rgb_array[:, :, 2] = B

    # Save output (no compression for precision)
    os.makedirs(os.path.dirname(OUTPUT_DEM), exist_ok=True)
    output_image = Image.fromarray(rgb_array, mode='RGB')
    output_image.save(OUTPUT_DEM, 'PNG', compress_level=0)

    print(f"✅ Terrain-RGB DEM saved: {OUTPUT_DEM}")
    print(f"Size: {output_image.size}")

    # Verify encoding (sample center pixel)
    center_y, center_x = height // 2, width // 2
    sample_r = int(R[center_y, center_x])
    sample_g = int(G[center_y, center_x])
    sample_b = int(B[center_y, center_x])
    decoded_height = -10000 + ((sample_r * 256 * 256 + sample_g * 256 + sample_b) * 0.1)
    original_height = height_meters[center_y, center_x]

    print(f"\n🔍 Encoding verification (center pixel):")
    print(f"  Original height: {original_height:.2f}m")
    print(f"  RGB: ({sample_r}, {sample_g}, {sample_b})")
    print(f"  Decoded height: {decoded_height:.2f}m")
    print(f"  Error: {abs(decoded_height - original_height):.4f}m")


if __name__ == "__main__":
    convert_heightmap_to_topographic()
    convert_heightmap_to_terrain_rgb()
