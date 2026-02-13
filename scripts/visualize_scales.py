#!/usr/bin/env python3
"""
Visualization script for spatial scales data.
Plots mean stock values averaged across time for each zoom level.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import sys

# Scale level configurations
SPATIAL_SCALES = {
    'level_0': {'scale': 8,  'description': 'Original 8km grid'},
    'level_1': {'scale': 11, 'description': 'Smooth scale (level 1)'},
    'level_2': {'scale': 15, 'description': 'Smooth scale (level 2)'},
    'level_3': {'scale': 21, 'description': 'Smooth scale (level 3)'},
    'level_4': {'scale': 29, 'description': 'Smooth scale (level 4)'},
    'level_5': {'scale': 41, 'description': 'Smooth scale (level 5)'},
    'level_6': {'scale': 64, 'description': 'Top 64km grid'},
}

SCALE_CONFIGS = {
    'level_0': {'scale': SPATIAL_SCALES['level_0']['scale'], 'color': '#1f77b4', 'marker': 'o', 'size': 20},
    'level_1': {'scale': SPATIAL_SCALES['level_1']['scale'], 'color': '#ff7f0e', 'marker': 's', 'size': 30},
    'level_2': {'scale': SPATIAL_SCALES['level_2']['scale'], 'color': '#2ca02c', 'marker': '^', 'size': 40},
    'level_3': {'scale': SPATIAL_SCALES['level_3']['scale'], 'color': '#d62728', 'marker': 'D', 'size': 50},
    'level_4': {'scale': SPATIAL_SCALES['level_4']['scale'], 'color': '#9467bd', 'marker': 'v', 'size': 60},
    'level_5': {'scale': SPATIAL_SCALES['level_5']['scale'], 'color': '#8c564b', 'marker': 'p', 'size': 80},
    'level_6': {'scale': SPATIAL_SCALES['level_6']['scale'], 'color': '#e377c2', 'marker': 'h', 'size': 100},
}

def load_and_aggregate_scale(filepath):
    """
    Load a scale file and compute mean stock across all time periods.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        DataFrame with LAMBX, LAMBY, mean_stock
    """
    print(f"  Loading {filepath.name}...")
    
    # Read the file
    df = pd.read_csv(filepath)
    
    # Check what columns are present
    has_week = 'week' in df.columns
    has_day = 'day' in df.columns
    
    # Group by spatial location and compute mean stock
    if has_week or has_day:
        spatial_cols = ['LAMBX', 'LAMBY']
        if 'grid_cell' in df.columns:
            spatial_cols.insert(0, 'grid_cell')
        
        # Aggregate: mean stock across all time periods for each location
        result = df.groupby(spatial_cols, as_index=False).agg({
            'Stock': 'mean',
            'point_count': 'first' if 'point_count' in df.columns else 'count'
        })
        
        result.rename(columns={'Stock': 'mean_stock'}, inplace=True)
    else:
        # Already aggregated or single time period
        result = df[['LAMBX', 'LAMBY', 'Stock']].copy()
        result.rename(columns={'Stock': 'mean_stock'}, inplace=True)
    
    print(f"    → {len(result)} spatial points with mean stock")
    return result


def plot_scale_level(ax, data, level, config, vmin=None, vmax=None):
    """
    Plot a single scale level on an axis.
    
    Args:
        ax: Matplotlib axis
        data: DataFrame with LAMBX, LAMBY, mean_stock
        level: Scale level name (e.g., 'level_0')
        config: Configuration dict with plotting parameters
        vmin, vmax: Color scale limits
    """
    if vmin is None:
        vmin = data['mean_stock'].min()
    if vmax is None:
        vmax = data['mean_stock'].max()
    
    # Create scatter plot
    scatter = ax.scatter(
        data['LAMBX'],
        data['LAMBY'],
        c=data['mean_stock'],
        s=config['size'],
        marker=config['marker'],
        cmap='YlOrRd',
        vmin=vmin,
        vmax=vmax,
        edgecolors='black',
        linewidths=0.5,
        alpha=0.8
    )
    
    ax.set_xlabel('LAMBX (km)', fontsize=10)
    ax.set_ylabel('LAMBY (km)', fontsize=10)
    ax.set_title(f"{level}: {config['scale']} km grid\n({len(data)} points)", 
                 fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_aspect('equal', adjustable='box')
    
    return scatter


def create_visualization(spatial_dir, output_file=None):
    """
    Create a multi-panel visualization of all scale levels.
    
    Args:
        spatial_dir: Directory containing the scale files
        output_file: Optional output file path for saving the figure
    """
    spatial_path = Path(spatial_dir)
    
    if not spatial_path.exists():
        print(f"Error: Directory '{spatial_dir}' not found!")
        return
    
    print(f"\n{'='*70}")
    print("SPATIAL SCALES VISUALIZATION")
    print(f"{'='*70}")
    print(f"Input directory: {spatial_dir}")
    
    # Find all scale files
    scale_files = {}
    for level in SCALE_CONFIGS.keys():
        # Look for files matching the pattern
        pattern = f"*{level}_*.csv"
        matches = list(spatial_path.glob(pattern))
        
        if matches:
            scale_files[level] = matches[0]
    
    if not scale_files:
        print("No scale files found!")
        print("Looking for files matching pattern: *level_N_*.csv")
        return
    
    print(f"\nFound {len(scale_files)} scale levels:")
    for level, filepath in sorted(scale_files.items()):
        scale = SCALE_CONFIGS[level]['scale']
        print(f"  {level}: {filepath.name} ({scale} km)")
    
    # Load data for all scales
    print("\nLoading data...")
    scale_data = {}
    all_stocks = []
    
    for level, filepath in sorted(scale_files.items()):
        data = load_and_aggregate_scale(filepath)
        scale_data[level] = data
        all_stocks.extend(data['mean_stock'].values)
    
    # Compute global min/max for consistent color scale
    vmin = np.percentile(all_stocks, 2)  # Use 2nd percentile to handle outliers
    vmax = np.percentile(all_stocks, 98)  # Use 98th percentile
    
    print(f"\nStock value range: {np.min(all_stocks):.1f} - {np.max(all_stocks):.1f}")
    print(f"Color scale range: {vmin:.1f} - {vmax:.1f}")
    
    # Create figure with subplots
    n_scales = len(scale_data)
    
    if n_scales <= 3:
        nrows, ncols = 1, n_scales
        figsize = (6 * ncols, 5)
    elif n_scales <= 6:
        nrows, ncols = 2, 3
        figsize = (18, 10)
    else:
        nrows, ncols = 3, 3
        figsize = (18, 15)
    
    print(f"\nCreating figure with {nrows}x{ncols} layout...")
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, squeeze=False)
    axes = axes.flatten()
    
    # Plot each scale level
    for idx, (level, data) in enumerate(sorted(scale_data.items())):
        config = SCALE_CONFIGS[level]
        ax = axes[idx]
        scatter = plot_scale_level(ax, data, level, config, vmin, vmax)
    
    # Hide unused subplots
    for idx in range(len(scale_data), len(axes)):
        axes[idx].set_visible(False)
    
    # Add a colorbar
    fig.subplots_adjust(right=0.92)
    cbar_ax = fig.add_axes([0.94, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(scatter, cax=cbar_ax)
    cbar.set_label('Mean Stock (mm)', fontsize=12, fontweight='bold')
    
    # Add main title
    fig.suptitle('Mean Stock Across Different Spatial Scales\n(Time-averaged values)', 
                 fontsize=14, fontweight='bold', y=0.98)
    
    plt.tight_layout(rect=[0, 0, 0.93, 0.96])
    
    # Save or show
    if output_file:
        output_path = Path(output_file)
        plt.savefig(output_path, dpi=450, bbox_inches='tight')
        print(f"\nFigure saved to: {output_path}")
    else:
        output_path = spatial_path / "spatial_scales_visualization.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nFigure saved to: {output_path}")
    
    print(f"\n{'='*70}")
    print("Visualization complete!")
    print(f"{'='*70}\n")
    
    return output_path


def create_single_scale_plot(filepath, output_file=None):
    """
    Create a simple plot for a single scale file.
    
    Args:
        filepath: Path to a single CSV file
        output_file: Optional output file path
    """
    print(f"\n{'='*70}")
    print("SINGLE SCALE VISUALIZATION")
    print(f"{'='*70}")
    
    filepath = Path(filepath)
    print(f"Input file: {filepath}")
    
    # Load data
    data = load_and_aggregate_scale(filepath)
    
    # Determine which level this is (if possible)
    level = None
    for lv in SCALE_CONFIGS.keys():
        if lv in filepath.name:
            level = lv
            break
    
    if level is None:
        # Use default config
        config = {'scale': '?', 'color': '#1f77b4', 'marker': 'o', 'size': 50}
    else:
        config = SCALE_CONFIGS[level]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    scatter = ax.scatter(
        data['LAMBX'],
        data['LAMBY'],
        c=data['mean_stock'],
        s=config['size'],
        marker=config['marker'],
        cmap='YlOrRd',
        edgecolors='black',
        linewidths=0.5,
        alpha=0.8
    )
    
    ax.set_xlabel('LAMBX (km)', fontsize=12)
    ax.set_ylabel('LAMBY (km)', fontsize=12)
    ax.set_title(f"Mean Stock - {config['scale']} km grid\n{len(data)} points (time-averaged)", 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_aspect('equal', adjustable='box')
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Mean Stock (mm)', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    
    # Save
    if output_file:
        output_path = Path(output_file)
    else:
        output_path = filepath.parent / f"{filepath.stem}_visualization.png"
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nFigure saved to: {output_path}")
    
    return output_path


def main():
    """Command line interface."""
    if len(sys.argv) < 2:
        print("""
Usage: python visualize_scales.py <spatial_scales_dir> [output_file]
   or: python visualize_scales.py <single_csv_file> [output_file]

Examples:
  # Visualize all scales in a directory
  python visualize_scales.py data/spatial_scales
  
  # Visualize all scales and save to specific file
  python visualize_scales.py data/spatial_scales output/all_scales.png
  
  # Visualize a single scale file
  python visualize_scales.py data/spatial_scales/data_level_2_32km.csv
""")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not input_path.exists():
        print(f"Error: '{input_path}' not found!")
        sys.exit(1)
    
    # Check if it's a directory or file
    if input_path.is_dir():
        create_visualization(input_path, output_file)
    elif input_path.is_file() and input_path.suffix == '.csv':
        create_single_scale_plot(input_path, output_file)
    else:
        print(f"Error: '{input_path}' is not a valid directory or CSV file!")
        sys.exit(1)


if __name__ == "__main__":
    main()
