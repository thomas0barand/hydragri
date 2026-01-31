import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import Point
from tqdm import tqdm

print("=== HYDRIC GAP CALCULATION WITH LOCATION-SPECIFIC KC ===\n")

# Load Kc and irrigation data calculated from commune agricultural data
print("Loading Kc and irrigation data for SAFRAN points...")
kc_data = pd.read_csv('data/safran_commune_kc.csv')
print(f"Loaded Kc data for {len(kc_data)} SAFRAN points")
print(kc_data[['LAMBX', 'LAMBY', 'avg_kc', 'pct_irrigated', 'pct_cereals', 'pct_prairies']])

# Load SIM data (ETP and P)
print("\nLoading SIM data...")
sim_path = Path("data/sim/QUOT_SIM2_reduced.csv")
df_sim = pd.read_csv(sim_path)
df_sim['DATE'] = pd.to_datetime(df_sim['DATE'], format='%Y%m%d')
print(f"SIM data loaded: {len(df_sim)} records")
print(f"Date range: {df_sim['DATE'].min()} to {df_sim['DATE'].max()}")

# Filter SIM data to only 2020 (to match agreste_2020 data)
df_sim = df_sim[df_sim['DATE'].dt.year == 2020]
print(f"Filtered to 2020: {len(df_sim)} records")

# Get unique SAFRAN points from Kc data
safran_points = kc_data[['LAMBX', 'LAMBY']].copy()
print(f"\nProcessing {len(safran_points)} SAFRAN points")

# Load shapefile with RU data
print("\nLoading RU shapefile...")
shp_path = Path("data/bdgsf_classe_ru/bdgsf_classe_ru.shp")
gdf_ru = gpd.read_file(shp_path)
print(f"RU shapefile loaded: {len(gdf_ru)} polygons")

# Create GeoDataFrame from SAFRAN points
# SAFRAN coordinates are in Lambert II étendu (EPSG:27582), in hectometers
print("\nCreating GeoDataFrame from SAFRAN points...")
geometry = [Point(x*100, y*100) for x, y in zip(safran_points['LAMBX'], safran_points['LAMBY'])]
gdf_points = gpd.GeoDataFrame(safran_points, geometry=geometry, crs="EPSG:27582")

# Spatial join to find RU for each point
print("Performing spatial join to find RU for each SAFRAN point...")
gdf_joined = gpd.sjoin(gdf_points, gdf_ru[['classe', 'geometry']], how='left', predicate='within')
gdf_joined = gdf_joined.drop_duplicates(subset=['LAMBX', 'LAMBY']).reset_index(drop=True)

# Map RU class to RU value (in mm)
ru_mapping = {
    1: 50,   # Very low
    2: 80,   # Low
    3: 100,  # Medium-low
    4: 120,  # Medium
    5: 150,  # Medium-high
    6: 180,  # High
    9: 200   # Very high
}
gdf_joined['RU_mm'] = gdf_joined['classe'].map(ru_mapping)

# Handle points without RU data (use default medium value)
default_ru = 120
gdf_joined['RU_mm'] = gdf_joined['RU_mm'].fillna(default_ru)

# Merge with Kc data
gdf_joined = gdf_joined.merge(kc_data, on=['LAMBX', 'LAMBY'], how='left')

print(f"\nRU and Kc values assigned to {len(gdf_joined)} points")
print(f"RU range: {gdf_joined['RU_mm'].min():.0f} - {gdf_joined['RU_mm'].max():.0f} mm")
print(f"Kc range: {gdf_joined['avg_kc'].min():.3f} - {gdf_joined['avg_kc'].max():.3f}")

# Process each point
print("\nCalculating water balance for each point...")
results = []

for idx, point_row in tqdm(gdf_joined.iterrows(), total=len(gdf_joined)):
    lambx, lamby = point_row['LAMBX'], point_row['LAMBY']
    ru_max = point_row['RU_mm']
    kc = point_row['avg_kc']
    pct_irrigated = point_row['pct_irrigated']
    pct_cereals = point_row['pct_cereals']
    pct_prairies = point_row['pct_prairies']
    pct_permanent = point_row['pct_permanent']
    pct_vineyards = point_row['pct_vineyards']
    
    # Get data for this point
    point_data = df_sim[(df_sim['LAMBX'] == lambx) & (df_sim['LAMBY'] == lamby)].copy()
    point_data = point_data.sort_values('DATE').reset_index(drop=True)
    
    if len(point_data) == 0:
        print(f"  WARNING: No SIM data for point ({lambx}, {lamby})")
        continue
    
    # Initialize Stock at RU_max (full at start of year)
    stock = ru_max
    
    # Calculate daily Stock and Gap
    for i, row in point_data.iterrows():
        date = row['DATE']
        p = row['PRE']
        etp = row['ETP']
        
        # Calculate daily water balance: Stock(j) = Stock(j-1) + P(j) - (ETP(j) * Kc)
        water_consumption = etp * kc
        stock = stock + p - water_consumption
        
        # Stock cannot exceed RU_max
        if stock > ru_max:
            stock = ru_max
        
        # Calculate Gap (when stock is negative, Gap = abs(stock))
        if stock < 0:
            gap = abs(stock)
            stock = 0
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
            'Kc': kc,
            'Stock': stock,
            'Gap': gap,
            'RU_max': ru_max,
            'pct_irrigated': pct_irrigated,
            'pct_cereals': pct_cereals,
            'pct_prairies': pct_prairies,
            'pct_permanent': pct_permanent,
            'pct_vineyards': pct_vineyards
        })

# Create DataFrame with results
df_results = pd.DataFrame(results)

# Save results
output_path = Path("data/gap_results_3samples_with_kc.csv")
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
    'Stock': ['min', 'mean'],
    'Kc': 'first',
    'pct_irrigated': 'first',
    'pct_cereals': 'first',
    'pct_prairies': 'first'
}).round(2)
print(summary)

# Show when Gap occurs
print("\n=== GAP ANALYSIS ===")
for point in df_results['point'].unique():
    point_df = df_results[df_results['point'] == point]
    days_with_gap = (point_df['Gap'] > 0).sum()
    total_gap = point_df['Gap'].sum()
    kc_val = point_df['Kc'].iloc[0]
    irrig_pct = point_df['pct_irrigated'].iloc[0]
    if days_with_gap > 0:
        first_gap = point_df[point_df['Gap'] > 0].iloc[0]['day']
        print(f"{point}: Kc={kc_val:.3f}, Irrigation={irrig_pct:.1f}%, {days_with_gap} days with Gap, Total Gap={total_gap:.2f} mm, First Gap on {first_gap.date()}")
    else:
        print(f"{point}: Kc={kc_val:.3f}, Irrigation={irrig_pct:.1f}%, No water deficit in 2020")

# Display sample of results
print("\n=== SAMPLE OUTPUT (first 20 rows) ===")
print(df_results.head(20).to_string(index=False))

print("\n=== PROCESSING COMPLETE ===")
