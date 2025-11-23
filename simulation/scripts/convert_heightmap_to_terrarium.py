#!/usr/bin/env python3
"""
Convert 16-bit grayscale heightmap to Terrarium DEM format for MapLibre 3D terrain.

Terrarium encoding: height = (R * 256 + G + B / 256) - 32768
This format is more robust than Mapbox terrain-rgb and widely supported.

Input: Heightmap.png (513x513, 16-bit grayscale)
Output: terrarium_dem.png (RGB encoded elevation data)
"""

import numpy as np
from PIL import Image
import os

# Configuration
INPUT_HEIGHTMAP = "/home/lecrabe/dev/evolutek/artefac-drone-defense/simulation/models/Harmonic Terrain/materials/textures/Heightmap.png"
OUTPUT_DEM = "/home/lecrabe/dev/evolutek/artefac-drone-defense/frontend/public/terrain/terrarium_dem.png"
MAX_HEIGHT_METERS = 201.66  # From model.sdf

def encode_terrarium(height_meters):
    """
    Encode elevation in meters to Terrarium RGB format.

    Formula: height = (R * 256 + G + B / 256) - 32768

    Args:
        height_meters: Elevation in meters (can be negative)

    Returns:
        (R, G, B) tuple (uint8)
    """
    # Offset to positive range (Terrarium uses -32768 to +32767 range)
    value = height_meters + 32768.0

    # Clamp to valid range
    value = np.clip(value, 0, 65535)

    # Extract RGB components
    R = np.floor(value / 256).astype(np.uint8)
    G = np.floor(value % 256).astype(np.uint8)
    B = np.floor((value % 1) * 256).astype(np.uint8)

    return R, G, B


def convert_heightmap_to_terrarium():
    """Convert 16-bit heightmap to Terrarium DEM format."""
    print(f"🗺️  Converting heightmap to Terrarium DEM format...")
    print(f"Input: {INPUT_HEIGHTMAP}")
    print(f"Output: {OUTPUT_DEM}")

    # Load 16-bit heightmap
    heightmap = Image.open(INPUT_HEIGHTMAP)
    height_array = np.array(heightmap, dtype=np.float32)

    print(f"Heightmap size: {height_array.shape}")
    print(f"Value range: {height_array.min():.0f} - {height_array.max():.0f} (16-bit)")

    # Normalize to meters (0-65535 → 0-MAX_HEIGHT_METERS)
    height_meters = (height_array / 65535.0) * MAX_HEIGHT_METERS

    print(f"Height in meters: {height_meters.min():.2f}m - {height_meters.max():.2f}m")

    # Encode to Terrarium RGB
    print("Encoding to Terrarium format...")
    R, G, B = encode_terrarium(height_meters)

    # Stack RGB channels
    rgb_array = np.stack([R, G, B], axis=-1)

    # Save output
    os.makedirs(os.path.dirname(OUTPUT_DEM), exist_ok=True)
    output_image = Image.fromarray(rgb_array, mode='RGB')
    output_image.save(OUTPUT_DEM, 'PNG', compress_level=9)

    print(f"✅ Terrarium DEM saved: {OUTPUT_DEM}")
    print(f"Size: {output_image.size}")

    # Verification: decode a sample pixel to check encoding
    sample_height = height_meters[256, 256]  # Center pixel
    sample_r, sample_g, sample_b = R[256, 256], G[256, 256], B[256, 256]
    decoded_height = (sample_r * 256 + sample_g + sample_b / 256) - 32768

    print(f"\n🔍 Encoding verification (center pixel):")
    print(f"  Original height: {sample_height:.2f}m")
    print(f"  RGB values: ({sample_r}, {sample_g}, {sample_b})")
    print(f"  Decoded height: {decoded_height:.2f}m")
    print(f"  Error: {abs(decoded_height - sample_height):.4f}m")

    # Statistics
    print(f"\n📊 Terrain Statistics:")
    print(f"  Min altitude: {height_meters.min():.2f}m")
    print(f"  Max altitude: {height_meters.max():.2f}m")
    print(f"  Avg altitude: {height_meters.mean():.2f}m")
    print(f"  Relief: {height_meters.max() - height_meters.min():.2f}m")


if __name__ == "__main__":
    convert_heightmap_to_terrarium()
