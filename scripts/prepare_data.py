import pandas as pd
import json
from pathlib import Path
from tqdm import tqdm

print("=== DATA PREPARATION FOR WEB APPLICATION ===\n")

# Load gap results
csv_path = Path("data/gap_results.csv")
df = pd.read_csv(csv_path)
df['day'] = pd.to_datetime(df['day'])

print(f"Loaded {len(df)} records for {df['point'].nunique()} points")

# Group by point and create structured data
points_data = []
points_metadata = []

for point_id in tqdm(df['point'].unique(), total=len(df['point'].unique())):
    point_df = df[df['point'] == point_id].copy()
    
    # Extract coordinates and metadata
    lambx = point_df['LAMBX'].iloc[0]
    lamby = point_df['LAMBY'].iloc[0]
    ru_max = point_df['RU_max'].iloc[0]
    
    # Calculate statistics
    total_gap = point_df['Gap'].sum()
    days_with_gap = (point_df['Gap'] > 0).sum()
    max_gap = point_df['Gap'].max()
    mean_stock = point_df['Stock'].mean()
    min_stock = point_df['Stock'].min()
    
    # Create time series (rounded to 2 decimals for web optimization)
    timeseries = []
    for _, row in point_df.iterrows():
        timeseries.append({
            'date': row['day'].strftime('%Y-%m-%d'),
            'P': round(row['P'], 2),
            'ETP': round(row['ETP'], 2),
            'Kc': round(row['Kc'], 2),
            'Stock': round(row['Stock'], 2),
            'Gap': round(row['Gap'], 2)
        })
    
    # Add to points data
    points_data.append({
        'id': point_id,
        'lambx': float(lambx),
        'lamby': float(lamby),
        'ru_max': float(ru_max),
        'total_gap': round(total_gap, 2),
        'days_with_gap': int(days_with_gap),
        'max_gap': round(max_gap, 2),
        'mean_stock': round(mean_stock, 2),
        'min_stock': round(min_stock, 2),
        'timeseries': timeseries
    })
    
    # Add to metadata (without full timeseries)
    points_metadata.append({
        'id': point_id,
        'lambx': float(lambx),
        'lamby': float(lamby),
        'ru_max': float(ru_max),
        'total_gap': round(total_gap, 2),
        'days_with_gap': int(days_with_gap),
        'max_gap': round(max_gap, 2),
        'mean_stock': round(mean_stock, 2),
        'min_stock': round(min_stock, 2)
    })

# Create output structure
output_data = {
    'points': points_data,
    'date_range': {
        'start': df['day'].min().strftime('%Y-%m-%d'),
        'end': df['day'].max().strftime('%Y-%m-%d')
    },
    'metadata': {
        'total_points': len(points_data),
        'total_records': len(df),
        'generated_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    }
}

# Save full data
output_path = Path("webapp/data/gap_data.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(output_data, f, indent=2)

print(f"\n✓ Saved full data to {output_path}")
print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")

# Save metadata only
metadata_output = {
    'points': points_metadata,
    'date_range': output_data['date_range'],
    'metadata': output_data['metadata']
}

metadata_path = Path("webapp/data/points_metadata.json")
with open(metadata_path, 'w') as f:
    json.dump(metadata_output, f, indent=2)

print(f"✓ Saved metadata to {metadata_path}")
print(f"  File size: {metadata_path.stat().st_size / 1024:.1f} KB")

# Summary statistics
print("\n=== SUMMARY STATISTICS ===")
for point in points_metadata:
    print(f"\nPoint {point['id']}:")
    print(f"  Coordinates: ({point['lambx']}, {point['lamby']})")
    print(f"  RU max: {point['ru_max']} mm")
    print(f"  Total Gap: {point['total_gap']} mm")
    print(f"  Days with Gap: {point['days_with_gap']}")

print("\n=== DATA PREPARATION COMPLETE ===")
