#!/usr/bin/env python3
"""
Simple visualization script for multi-scale grid data on France map.
Handles Lambert-93 (EPSG:2154) to WGS84 (EPSG:4326) conversion.

Required packages: pip install folium pyproj pandas
"""

import pandas as pd
import folium
from pathlib import Path
import sys


# Check if pyproj is available for proper coordinate conversion
try:
    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
    HAS_PYPROJ = True
except ImportError:
    print("Warning: pyproj not found. Using approximate coordinate conversion.")
    print("For accurate results, install: pip install pyproj")
    HAS_PYPROJ = False
    transformer = None


def lambert93_to_wgs84(x, y):
    """Convert Lambert-93 (EPSG:2154) to WGS84 (EPSG:4326)."""
    if HAS_PYPROJ and transformer:
        lon, lat = transformer.transform(x, y)
        return lat, lon
    else:
        # Rough approximation (not accurate!)
        lon = (x - 700000) / 111320.0 + 3.0
        lat = (y - 6600000) / 110540.0 + 46.5
        return lat, lon


def get_color(value, vmin, vmax):
    """Simple color scale: blue (low) -> yellow -> red (high)."""
    if pd.isna(value) or vmax == vmin:
        return '#808080'
    
    norm = (value - vmin) / (vmax - vmin)
    
    if norm < 0.5:
        # Blue to yellow
        r = int(255 * norm * 2)
        g = int(255 * norm * 2)
        b = int(255 * (1 - norm * 2))
    else:
        # Yellow to red
        r = 255
        g = int(255 * (1 - (norm - 0.5) * 2))
        b = 0
    
    return f'#{r:02x}{g:02x}{b:02x}'


def create_simple_map(data_file, metric='Gap', output='map.html'):
    """
    Create a simple map from a single scale file.
    
    Args:
        data_file: Path to CSV file
        metric: Column to visualize
        output: Output HTML file
    """
    print(f"Loading {data_file}...")
    df = pd.read_csv(data_file)
    
    # Get scale from filename
    fname = Path(data_file).stem
    if 'km' in fname:
        scale_km = int(fname.split('_')[-1].replace('km', ''))
    else:
        scale_km = 8  # default
    
    print(f"Grid scale: {scale_km} km")
    
    # Aggregate by grid cell if weekly data
    if 'week' in df.columns:
        print("Averaging across all weeks...")
        df = df.groupby(['grid_cell', 'LAMBX', 'LAMBY'], as_index=False)[metric].mean()
    
    print(f"Grid cells: {len(df)}")
    
    # Create map centered on France
    m = folium.Map(location=[46.5, 2.0], zoom_start=6, tiles='OpenStreetMap')
    
    # Get value range for colors
    vmin = df[metric].min()
    vmax = df[metric].max()
    print(f"{metric} range: {vmin:.2f} - {vmax:.2f}")
    
    # Cell size in degrees (approximate)
    cell_deg = scale_km / 111.0
    
    # Add grid cells
    print("Creating grid cells...")
    for idx, row in df.iterrows():
        lat, lon = lambert93_to_wgs84(row['LAMBX'], row['LAMBY'])
        value = row[metric]
        color = get_color(value, vmin, vmax)
        
        # Rectangle bounds
        bounds = [
            [lat - cell_deg/2, lon - cell_deg/2],
            [lat + cell_deg/2, lon + cell_deg/2]
        ]
        
        # Popup
        popup = f"<b>{metric}:</b> {value:.2f}<br><b>Grid:</b> {row.get('grid_cell', 'N/A')}"
        
        folium.Rectangle(
            bounds=bounds,
            popup=popup,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.6,
            weight=1
        ).add_to(m)
        
        if (idx + 1) % 100 == 0:
            print(f"  {idx + 1}/{len(df)} cells...", end='\r')
    
    print(f"  {len(df)}/{len(df)} cells - Done!")
    
    # Add title
    title = f'''
    <div style="position: fixed; top: 10px; left: 50px; 
                background-color: white; border: 2px solid grey; 
                padding: 10px; z-index: 9999;">
    <h3 style="margin: 0;">{scale_km} km Grid - {metric}</h3>
    <p style="margin: 5px 0;">Min: {vmin:.2f} | Max: {vmax:.2f}</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title))
    
    # Save
    m.save(output)
    print(f"\nMap saved: {output}")
    print(f"Open in browser to view!")
    
    return output


def create_multi_scale_map(scale_dir, metric='Gap', output='multi_scale_map.html'):
    """
    Create map with all scales as layer options.
    
    Args:
        scale_dir: Directory with scale files
        metric: Column to visualize
        output: Output HTML file
    """
    scale_dir = Path(scale_dir)
    
    # Find all scale files
    scale_files = sorted(scale_dir.glob('*_level_*.csv'))
    
    if not scale_files:
        print(f"No scale files found in {scale_dir}")
        return None
    
    print(f"Found {len(scale_files)} scale files")
    
    # Create base map
    m = folium.Map(location=[46.5, 2.0], zoom_start=6, tiles='CartoDB positron')
    
    # Add each scale as a layer
    for file in scale_files:
        # Extract scale info
        fname = file.stem
        level = int(fname.split('level_')[1].split('_')[0])
        scale_km = int(fname.split('_')[-1].replace('km', ''))
        
        print(f"\nProcessing level_{level} ({scale_km} km)...")
        
        # Load data
        df = pd.read_csv(file)
        
        # Aggregate if weekly
        if 'week' in df.columns:
            df = df.groupby(['grid_cell', 'LAMBX', 'LAMBY'], as_index=False)[metric].mean()
        
        print(f"  Grid cells: {len(df)}")
        
        # Get value range
        vmin = df[metric].min()
        vmax = df[metric].max()
        
        # Create layer
        layer = folium.FeatureGroup(name=f'{scale_km} km ({len(df)} cells)', show=(level == 0))
        
        # Cell size
        cell_deg = scale_km / 111.0
        
        # Add cells
        for idx, row in df.iterrows():
            lat, lon = lambert93_to_wgs84(row['LAMBX'], row['LAMBY'])
            value = row[metric]
            color = get_color(value, vmin, vmax)
            
            bounds = [
                [lat - cell_deg/2, lon - cell_deg/2],
                [lat + cell_deg/2, lon + cell_deg/2]
            ]
            
            popup = f"<b>Scale:</b> {scale_km} km<br><b>{metric}:</b> {value:.2f}"
            
            folium.Rectangle(
                bounds=bounds,
                popup=popup,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.6,
                weight=1,
                opacity=0.8
            ).add_to(layer)
        
        layer.add_to(m)
        print(f"  Added to map!")
    
    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Add title
    title = f'''
    <div style="position: fixed; top: 10px; left: 50px; 
                background-color: white; border: 2px solid grey; 
                padding: 10px; z-index: 9999;">
    <h3 style="margin: 0;">Multi-Scale Grid Visualization</h3>
    <p style="margin: 5px 0;"><b>Metric:</b> {metric}</p>
    <p style="margin: 5px 0;">Use layer control → to switch scales</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title))
    
    # Save
    m.save(output)
    print(f"\n{'='*60}")
    print(f"Map saved: {output}")
    print(f"{'='*60}")
    
    return output


def main():
    if len(sys.argv) < 2:
        print("""
Simple Multi-Scale Map Visualization

Usage:
  python visualize_simple.py <file_or_directory> [options]

Options:
  --metric <name>   Metric to display: Gap, P, ETP, Stock (default: Gap)
  --output <file>   Output HTML file (default: map.html)

Examples:
  # Single scale file
  python visualize_simple.py data_level_0_8km.csv
  
  # All scales from directory
  python visualize_simple.py spatial_scales/
  
  # Different metric
  python visualize_simple.py spatial_scales/ --metric P --output precip_map.html
""")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    
    # Parse options
    metric = 'Gap'
    output = 'map.html'
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--metric' and i + 1 < len(sys.argv):
            metric = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    # Check if path exists
    if not path.exists():
        print(f"Error: {path} not found!")
        sys.exit(1)
    
    # Process based on type
    if path.is_file():
        create_simple_map(str(path), metric, output)
    elif path.is_dir():
        create_multi_scale_map(path, metric, output)
    else:
        print(f"Error: {path} is not a file or directory!")
        sys.exit(1)


if __name__ == "__main__":
    main()