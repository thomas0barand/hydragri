#!/usr/bin/env python3
"""
Multi-scale aggregation script for gap_results data.
Provides both temporal (weekly) and spatial (grid-based) aggregation
for efficient map visualization at different zoom levels.

Original grid: 8 km spacing
Spatial scales: 8 km, 16 km, 32 km, 64 km, 128 km, 256 km, 512 km (7 levels)
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path


# ============================================================================
# CONFIGURATION: SPATIAL AGGREGATION SCALES
# ============================================================================

SPATIAL_SCALES = {
    'level_0': {'scale': 8, 'description': 'Original 8km grid'},
    'level_1': {'scale': 11, 'description': 'Smooth scale (level 1)'},
    'level_2': {'scale': 15, 'description': 'Smooth scale (level 2)'},
    'level_3': {'scale': 21, 'description': 'Smooth scale (level 3)'},
    'level_4': {'scale': 29, 'description': 'Smooth scale (level 4)'},
    'level_5': {'scale': 41, 'description': 'Smooth scale (level 5)'},
    'level_6': {'scale': 64, 'description': 'Top 64km grid'},
}

# Recommended zoom levels for each scale (if using web maps like Leaflet/Mapbox)
ZOOM_RECOMMENDATIONS = {
    'level_0': 'zoom >= 10',  # 8km - detailed view
    'level_1': 'zoom 9-10',   # 16km
    'level_2': 'zoom 8-9',    # 32km
    'level_3': 'zoom 7-8',    # 64km
    'level_4': 'zoom 6-7',    # 128km
    'level_5': 'zoom 5-6',    # 256km
    'level_6': 'zoom <= 5',   # 512km - overview
}


# ============================================================================
# TEMPORAL AGGREGATION: Daily → Weekly
# ============================================================================

def aggregate_temporal(input_file, output_file=None, chunksize=500000):
    """
    Aggregate daily data to weekly averages.
    Streams output to disk to avoid OOM on large multi-year datasets.
    """
    input_path = Path(input_file)
    if output_file is None:
        output_file = input_path.parent / f"{input_path.stem}_weekly.csv"

    print(f"\n{'='*70}")
    print("TEMPORAL AGGREGATION: Daily → Weekly (2020-2025)")
    print(f"{'='*70}")
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")

    # Truncate output file if it exists
    Path(output_file).unlink(missing_ok=True)

    # First pass: aggregate per chunk and collect partial results
    # Since input is sorted by point, most weeks are complete within a chunk
    print("\nProcessing in chunks...")
    total_rows = 0
    header_written = False
    prev_tail = None  # leftover rows from previous chunk (incomplete last point)

    for chunk in pd.read_csv(input_file, chunksize=chunksize):
        # Drop stray header rows embedded in data (from interrupted streaming writes)
        chunk = chunk[chunk['LAMBX'] != 'LAMBX'].copy()
        chunk['LAMBX'] = chunk['LAMBX'].astype('float32')
        chunk['LAMBY'] = chunk['LAMBY'].astype('float32')
        for c in ['P', 'ETP', 'Stock', 'Gap']:
            chunk[c] = chunk[c].astype('float32')
        total_rows += len(chunk)

        chunk['day'] = pd.to_datetime(chunk['day'])
        chunk['week'] = chunk['day'].dt.strftime('%Y-W%W')

        # Prepend leftover from previous chunk
        if prev_tail is not None:
            chunk = pd.concat([prev_tail, chunk], ignore_index=True)
            prev_tail = None

        # Keep the last point aside (may be split across chunks)
        last_point = chunk['point'].iloc[-1]
        tail_mask = chunk['point'] == last_point
        prev_tail = chunk[tail_mask].copy()
        chunk = chunk[~tail_mask]

        if len(chunk) == 0:
            continue

        agg = chunk.groupby(['point', 'LAMBX', 'LAMBY', 'week'], as_index=False).agg({
            'P': 'mean', 'ETP': 'mean', 'Stock': 'mean', 'Gap': 'mean'
        })
        agg.to_csv(output_file, mode='a', index=False, header=not header_written)
        header_written = True
        print(f"  Processed {total_rows:,} rows...", end='\r')

    # Flush the last point
    if prev_tail is not None and len(prev_tail) > 0:
        agg = prev_tail.groupby(['point', 'LAMBX', 'LAMBY', 'week'], as_index=False).agg({
            'P': 'mean', 'ETP': 'mean', 'Stock': 'mean', 'Gap': 'mean'
        })
        agg.to_csv(output_file, mode='a', index=False, header=not header_written)

    # Count output rows
    out_rows = sum(1 for _ in open(output_file)) - 1
    reduction = (1 - out_rows / total_rows) * 100 if total_rows > 0 else 0
    print(f"\n  Total rows read: {total_rows:,}")
    print(f"  Aggregated rows: {out_rows:,}")
    print(f"  Reduction:       {reduction:.1f}%")
    print(f"  Saved to:        {output_file}")

    return output_file


# ============================================================================
# SPATIAL AGGREGATION: Grid-based multi-scale
# ============================================================================

def aggregate_spatial(input_file, output_dir=None, scale_level=None, 
                     base_grid_size=8, chunksize=100000):
    """
    Aggregate points spatially to coarser grids for multi-scale visualization.
    
    Args:
        input_file: Path to input CSV file (can be daily or weekly data)
        output_dir: Directory for output files (optional, auto-generated if None)
        scale_level: Specific level to process (e.g., 'level_1'), or None for all
        base_grid_size: Original grid spacing in km (default: 8)
        chunksize: Number of rows to process at once
    
    Returns:
        Dictionary of output file paths by level
    """
    input_path = Path(input_file)
    
    if output_dir is None:
        output_dir = input_path.parent / "spatial_scales"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(exist_ok=True, parents=True)
    
    print(f"\n{'='*70}")
    print("SPATIAL AGGREGATION: Multi-scale grid generation")
    print(f"{'='*70}")
    print(f"Input:      {input_file}")
    print(f"Output dir: {output_dir}")
    print(f"Base grid:  {base_grid_size} km")
    
    # Determine which levels to process
    if scale_level:
        if scale_level not in SPATIAL_SCALES:
            raise ValueError(f"Invalid scale_level. Choose from {list(SPATIAL_SCALES.keys())}")
        levels_to_process = {scale_level: SPATIAL_SCALES[scale_level]}
    else:
        levels_to_process = SPATIAL_SCALES
    
    print(f"\nProcessing {len(levels_to_process)} scale level(s):")
    for level, info in levels_to_process.items():
        print(f"  {level}: {info['description']} - {ZOOM_RECOMMENDATIONS[level]}")
    
    output_files = {}
    
    # Read the entire file (weekly data should be small enough)
    print("\nLoading data...")
    dtype_dict = {
        'point': str,
        'LAMBX': 'float64',  # Use float64 for better precision
        'LAMBY': 'float64',
        'P': 'float32',
        'ETP': 'float32',
        'Stock': 'float32',
        'Gap': 'float32'
    }
    
    # Check if it's daily or weekly data
    df = pd.read_csv(input_file, dtype=dtype_dict, nrows=5)
    has_week = 'week' in df.columns
    has_day = 'day' in df.columns
    
    if has_day:
        df = pd.read_csv(input_file, dtype=dtype_dict)
        time_col = 'day'
        print(f"  Detected daily data: {len(df):,} rows")
    elif has_week:
        df = pd.read_csv(input_file, dtype=dtype_dict)
        time_col = 'week'
        print(f"  Detected weekly data: {len(df):,} rows")
    else:
        raise ValueError("No 'day' or 'week' column found in input file")
    
    # Analyze coordinate system
    print("\nAnalyzing coordinate system...")
    x_min, x_max = df['LAMBX'].min(), df['LAMBX'].max()
    y_min, y_max = df['LAMBY'].min(), df['LAMBY'].max()
    unique_points = df[['LAMBX', 'LAMBY']].drop_duplicates()
    
    print(f"  X range: {x_min:,.0f} to {x_max:,.0f} (span: {x_max-x_min:,.0f})")
    print(f"  Y range: {y_min:,.0f} to {y_max:,.0f} (span: {y_max-y_min:,.0f})")
    print(f"  Unique spatial points: {len(unique_points):,}")
    
    # Auto-detect if coordinates are in km or meters
    # If coordinates are small (< 10000), they're likely in km
    # Lambert 93 coordinates in France are typically 6-7 digits (hundreds of thousands)
    if x_max < 10000 and y_max < 100000:
        print("  → Detected coordinates in KILOMETERS")
        coord_unit = 10  # Convert km to meters
        print(f"  → Converting to meters for grid calculation")
    else:
        print("  → Detected coordinates in METERS (Lambert 93 projection)")
        coord_unit = 1  # Already in meters
    
    # Convert coordinates to meters if needed
    df['X_meters'] = df['LAMBX'] * coord_unit
    df['Y_meters'] = df['LAMBY'] * coord_unit
    
    # Process each scale level
    for level, info in levels_to_process.items():
        scale = info['scale']
        grid_size_meters = scale * 10  # Convert km to meters
        
        print(f"\n  Processing {level} ({scale} km = {grid_size_meters:,} m grid)...")
        
        # Calculate grid cell for each point using floor division for consistent binning
        # This ensures points are grouped into proper grid cells
        df['grid_x'] = (np.floor(df['X_meters'] / grid_size_meters) * grid_size_meters).astype('float64')
        df['grid_y'] = (np.floor(df['Y_meters'] / grid_size_meters) * grid_size_meters).astype('float64')
        
        # Use the center of the grid cell as the representative coordinate
        df['grid_x_center'] = df['grid_x'] + grid_size_meters / 2
        df['grid_y_center'] = df['grid_y'] + grid_size_meters / 2
        
        # Create grid cell identifier
        df['grid_cell'] = df['grid_x'].astype(str) + '_' + df['grid_y'].astype(str)
        
        # Group by grid cell and time, then aggregate
        if has_week:
            group_cols = ['grid_cell', 'grid_x_center', 'grid_y_center', 'week']
        else:
            group_cols = ['grid_cell', 'grid_x_center', 'grid_y_center', 'day']
        
        aggregated = df.groupby(group_cols, as_index=False).agg({
            'P': 'mean',
            'ETP': 'mean',
            'Stock': 'mean',
            'Gap': 'mean',
            'point': 'count'  # Count of original points in this grid cell
        })
        
        # Convert back to original coordinate units (km if input was km)
        aggregated['LAMBX'] = aggregated['grid_x_center'] / coord_unit
        aggregated['LAMBY'] = aggregated['grid_y_center'] / coord_unit
        
        # Rename columns
        aggregated = aggregated.rename(columns={
            'point': 'point_count'
        })
        
        # Reorder columns
        if has_week:
            aggregated = aggregated[['grid_cell', 'LAMBX', 'LAMBY', 'week', 
                                    'P', 'ETP', 'Stock', 'Gap', 'point_count']]
        else:
            aggregated = aggregated[['grid_cell', 'LAMBX', 'LAMBY', 'day', 
                                    'P', 'ETP', 'Stock', 'Gap', 'point_count']]
        
        # Sort
        aggregated = aggregated.sort_values(['grid_cell', time_col]).reset_index(drop=True)
        
        # Save to file
        output_file = output_dir / f"{input_path.stem}_{level}_{scale}km.csv"
        aggregated.to_csv(output_file, index=False)
        output_files[level] = output_file
        
        unique_orig_cells = len(unique_points)
        unique_agg_cells = aggregated['grid_cell'].nunique()
        reduction = (1 - len(aggregated) / len(df)) * 100
        spatial_reduction = (1 - unique_agg_cells / unique_orig_cells) * 100 if unique_orig_cells > 0 else 0
        
        print(f"    Original spatial cells: {unique_orig_cells:,}")
        print(f"    Aggregated cells:       {unique_agg_cells:,}")
        print(f"    Spatial reduction:      {spatial_reduction:.1f}%")
        print(f"    Total rows:             {len(aggregated):,}")
        print(f"    Total reduction:        {reduction:.1f}%")
        print(f"    Avg points per cell:    {aggregated['point_count'].mean():.1f}")
        print(f"    Saved to:               {output_file.name}")
    
    # Clean up temporary columns
    df.drop(['X_meters', 'Y_meters', 'grid_x', 'grid_y', 'grid_x_center', 'grid_y_center', 'grid_cell'], 
            axis=1, errors='ignore', inplace=True)
    
    # Create a metadata file
    metadata_file = output_dir / "scales_metadata.txt"
    with open(metadata_file, 'w') as f:
        f.write("SPATIAL SCALES METADATA\n")
        f.write("="*70 + "\n\n")
        f.write(f"Base grid size: {base_grid_size} km\n")
        f.write(f"Source file: {input_file}\n")
        f.write(f"Coordinate unit: {'kilometers' if coord_unit == 1000 else 'meters'}\n")
        f.write(f"Projection: Lambert 93 (EPSG:2154) assumed\n\n")
        f.write(f"Data extent:\n")
        f.write(f"  X: {x_min:,.0f} to {x_max:,.0f}\n")
        f.write(f"  Y: {y_min:,.0f} to {y_max:,.0f}\n")
        f.write(f"  Unique points: {len(unique_points):,}\n\n")
        f.write("Scale Levels:\n")
        f.write("-" * 70 + "\n")
        for level, info in SPATIAL_SCALES.items():
            f.write(f"\n{level}:\n")
            f.write(f"  Grid size: {info['scale']} km\n")
            f.write(f"  Description: {info['description']}\n")
            f.write(f"  Recommended zoom: {ZOOM_RECOMMENDATIONS[level]}\n")
            if level in output_files:
                f.write(f"  File: {output_files[level].name}\n")
    
    print(f"\n  Metadata saved to: {metadata_file}")
    print(f"\n{'='*70}")
    print(f"Spatial aggregation complete! {len(output_files)} files created.")
    print(f"{'='*70}\n")
    
    return output_files


# ============================================================================
# COMBINED WORKFLOW: Temporal + Spatial
# ============================================================================

def aggregate_temporal_and_spatial(input_file, output_base_dir=None, 
                                   temporal_only=False, spatial_only=False,
                                   base_grid_size=8):
    """
    Complete workflow: temporal aggregation followed by spatial aggregation.
    
    Args:
        input_file: Path to input CSV with daily data
        output_base_dir: Base directory for all outputs
        temporal_only: Only perform temporal aggregation
        spatial_only: Only perform spatial aggregation (input must be weekly)
        base_grid_size: Original grid spacing in km
    
    Returns:
        Dictionary with paths to all generated files
    """
    input_path = Path(input_file)
    
    if output_base_dir is None:
        output_base_dir = input_path.parent / "aggregated_data"
    else:
        output_base_dir = Path(output_base_dir)
    
    output_base_dir.mkdir(exist_ok=True, parents=True)
    
    results = {
        'weekly_file': None,
        'spatial_files': {}
    }
    
    print(f"\n{'#'*70}")
    print("MULTI-SCALE AGGREGATION WORKFLOW")
    print(f"{'#'*70}")
    
    # Step 1: Temporal aggregation
    if not spatial_only:
        weekly_file = output_base_dir / f"{input_path.stem}_weekly.csv"
        results['weekly_file'] = aggregate_temporal(input_file, weekly_file)
    else:
        weekly_file = input_file
        print("\nSkipping temporal aggregation (spatial_only=True)")
    
    if temporal_only:
        print("\nSkipping spatial aggregation (temporal_only=True)")
        return results
    
    # Step 2: Spatial aggregation
    spatial_dir = output_base_dir / "spatial_scales"
    results['spatial_files'] = aggregate_spatial(
        weekly_file, 
        spatial_dir, 
        base_grid_size=base_grid_size
    )
    
    # Create summary file
    summary_file = output_base_dir / "aggregation_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("AGGREGATION SUMMARY\n")
        f.write("="*70 + "\n\n")
        f.write(f"Source file: {input_file}\n")
        f.write(f"Output directory: {output_base_dir}\n\n")
        
        if results['weekly_file']:
            f.write(f"Weekly aggregated file:\n  {results['weekly_file']}\n\n")
        
        f.write(f"Spatial scale files ({len(results['spatial_files'])}):\n")
        for level, filepath in results['spatial_files'].items():
            scale = SPATIAL_SCALES[level]['scale']
            f.write(f"  {level} ({scale:3d} km): {filepath.name}\n")
    
    print(f"\nSummary saved to: {summary_file}")
    print(f"\n{'#'*70}")
    print("ALL AGGREGATIONS COMPLETE!")
    print(f"{'#'*70}\n")
    
    return results


# ============================================================================
# MAIN / CLI
# ============================================================================

def main():
    """Command line interface."""
    if len(sys.argv) < 2:
        print("""
Usage: python aggregate_multi_scale.py <command> <input_file> [options]

Commands:
  temporal     - Aggregate daily data to weekly
  spatial      - Aggregate to multiple spatial scales
  both         - Do both temporal and spatial aggregation

Examples:
  # Temporal only
  python aggregate_multi_scale.py temporal gap_results.csv
  
  # Spatial only (input should be weekly data)
  python aggregate_multi_scale.py spatial gap_results_weekly.csv
  
  # Both (complete workflow)
  python aggregate_multi_scale.py both gap_results.csv
  
  # Specify output directory
  python aggregate.py both data/gap_results_with_kc.csv data/

Options:
  --base-grid-size <km>  Set base grid size (default: 8)
""")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if len(sys.argv) < 3:
        print("Error: Input file required")
        sys.exit(1)
    
    input_file = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Check base grid size
    base_grid_size = 8
    if '--base-grid-size' in sys.argv:
        idx = sys.argv.index('--base-grid-size')
        if idx + 1 < len(sys.argv):
            base_grid_size = int(sys.argv[idx + 1])
    
    if not Path(input_file).exists():
        print(f"Error: Input file '{input_file}' not found!")
        sys.exit(1)
    
    # Execute command
    if command == 'temporal':
        aggregate_temporal(input_file, output_dir)
    elif command == 'spatial':
        aggregate_spatial(input_file, output_dir, base_grid_size=base_grid_size)
    elif command == 'both':
        aggregate_temporal_and_spatial(input_file, output_dir, base_grid_size=base_grid_size)
    else:
        print(f"Error: Unknown command '{command}'")
        print("Valid commands: temporal, spatial, both")
        sys.exit(1)


if __name__ == "__main__":
    main()