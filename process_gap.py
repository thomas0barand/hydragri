import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import Point
from tqdm import tqdm

# Universal crop coefficient (as mentioned in the PDF, typical value for growing season)
KC_UNIVERSAL = 0.9

print("=== HYDRIC GAP CALCULATION ===\n")

# Load SIM data (ETP and P)
print("Loading SIM data...")
sim_path = Path("data/sim/QUOT_SIM2_reduced.csv")
df_sim = pd.read_csv(sim_path)
df_sim['DATE'] = pd.to_datetime(df_sim['DATE'], format='%Y%m%d')
print(f"SIM data loaded: {len(df_sim)} records")
print(f"Date range: {df_sim['DATE'].min()} to {df_sim['DATE'].max()}")

# Get unique SAFRAN points
unique_points = df_sim[['LAMBX', 'LAMBY']].drop_duplicates().reset_index(drop=True)
print(f"Unique SAFRAN points: {len(unique_points)}")

# Load shapefile with RU data
print("\nLoading RU shapefile...")
shp_path = Path("data/bdgsf_classe_ru/bdgsf_classe_ru.shp")
gdf_ru = gpd.read_file(shp_path)
print(f"RU shapefile loaded: {len(gdf_ru)} polygons")
print(f"RU classes: {sorted(gdf_ru['classe'].unique())}")
print(f"Shapefile CRS: {gdf_ru.crs} (Lambert II étendu)")

# Create GeoDataFrame from SAFRAN points
# IMPORTANT: SAFRAN coordinates are in Lambert II étendu (EPSG:27582), in hectometers
print("\nCreating GeoDataFrame from SAFRAN points...")
print(f"SAFRAN coordinates in hectometers (x100 = meters)")
# SAFRAN coordinates are in hectometers (100m units), multiply by 100 to get meters
geometry = [Point(x*100, y*100) for x, y in zip(unique_points['LAMBX'], unique_points['LAMBY'])]
# Use same CRS as RU shapefile (EPSG:27582 - Lambert II étendu)
gdf_points = gpd.GeoDataFrame(unique_points, geometry=geometry, crs="EPSG:27582")

print(f"SAFRAN points bounds: {gdf_points.total_bounds}")
print(f"RU shapefile bounds:  {gdf_ru.total_bounds}")
print(f"CRS match: {gdf_points.crs == gdf_ru.crs}")

# Spatial join to find RU for each point
print("\nPerforming spatial join to find RU for each SAFRAN point...")
gdf_joined = gpd.sjoin(gdf_points, gdf_ru[['classe', 'geometry']], how='left', predicate='within')
gdf_joined = gdf_joined.drop_duplicates(subset=['LAMBX', 'LAMBY']).reset_index(drop=True)

# Map RU class to RU value (in mm)
# Based on typical soil water holding capacity classes
ru_mapping = {
    1: 50,   # Very low
    2: 80,   # Low
    3: 100,  # Medium-low
    4: 120,  # Medium
    5: 150,  # Medium-high
    6: 180,  # High
    9: 200   # Very high (class 9 seen in data)
}
gdf_joined['RU_mm'] = gdf_joined['classe'].map(ru_mapping)

# Handle points without RU data (use default medium value)
default_ru = 120
points_with_ru = gdf_joined['RU_mm'].notna().sum()
print(f"Points with RU data: {points_with_ru}/{len(gdf_joined)}")
gdf_joined['RU_mm'] = gdf_joined['RU_mm'].fillna(default_ru)

print(f"\nRU values assigned to {len(gdf_joined)} points")
print(f"RU range: {gdf_joined['RU_mm'].min():.0f} - {gdf_joined['RU_mm'].max():.0f} mm")

# Select a few points for testing (first 3 points)
n_test_points = 3
test_points = gdf_joined[['LAMBX', 'LAMBY', 'RU_mm']]
print(f"\nProcessing {n_test_points} test points:")
for idx, row in test_points.iterrows():
    print(f"  Point ({row['LAMBX']}, {row['LAMBY']}): RU = {row['RU_mm']:.0f} mm")

# Process each test point
results = []

for idx, point_row in tqdm(test_points.iterrows(), total=len(test_points)):
    lambx, lamby, ru_max = point_row['LAMBX'], point_row['LAMBY'], point_row['RU_mm']
        
    # Get data for this point
    point_data = df_sim[(df_sim['LAMBX'] == lambx) & (df_sim['LAMBY'] == lamby)].copy()
    point_data = point_data.sort_values('DATE').reset_index(drop=True)
    
    # Initialize Stock at RU_max (full at start of year)
    stock = ru_max
    
    # Calculate daily Stock and Gap
    for i, row in point_data.iterrows():
        date = row['DATE']
        p = row['PRE']
        etp = row['ETP']
        
        # Calculate daily water balance: Stock(j) = Stock(j-1) + P(j) - (ETP(j) * Kc)
        water_consumption = etp * KC_UNIVERSAL
        stock = stock + p - water_consumption
        
        # Stock cannot exceed RU_max
        if stock > ru_max:
            stock = ru_max
        
        # Calculate Gap (when stock is negative, Gap = abs(stock))
        # Gap represents the water deficit
        if stock < 0:
            gap = abs(stock)
            stock = 0  # Stock cannot be negative
        else:
            gap = 0
        
        # Store results
        results.append({
            'point': f"({lambx},{lamby})",
            'LAMBX': lambx,
            'LAMBY': lamby,
            'day': date,
            'P': p,
            'ETP': etp,
            'Kc': KC_UNIVERSAL,
            'Stock': stock,
            'Gap': gap,
            'RU_max': ru_max
        })

# Create DataFrame with results
df_results = pd.DataFrame(results)

# Save results
output_path = Path("data/gap_results.csv")
df_results.to_csv(output_path, index=False)
print(f"\n=== RESULTS SAVED ===")
print(f"Output file: {output_path}")
print(f"Total records: {len(df_results)}")

# Display summary statistics
print("\n=== SUMMARY STATISTICS ===")
summary = df_results.groupby('point').agg({
    'P': 'sum',
    'ETP': 'sum',
    'Gap': ['sum', 'max', 'mean'],
    'Stock': ['min', 'mean']
}).round(2)
print(summary)

# Show when Gap occurs
print("\n=== GAP ANALYSIS ===")
for point in df_results['point'].unique():
    point_df = df_results[df_results['point'] == point]
    days_with_gap = (point_df['Gap'] > 0).sum()
    total_gap = point_df['Gap'].sum()
    if days_with_gap > 0:
        first_gap = point_df[point_df['Gap'] > 0].iloc[0]['day']
        print(f"{point}: {days_with_gap} days with Gap, Total Gap = {total_gap:.2f} mm, First Gap on {first_gap.date()}")

# Display sample of results
print("\n=== SAMPLE OUTPUT (first 20 rows) ===")
print(df_results.head(20).to_string(index=False))

print("\n=== PROCESSING COMPLETE ===")
