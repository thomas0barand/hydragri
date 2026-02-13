import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import Point
from tqdm import tqdm

YEARS = range(2020, 2026)  # 2020 to 2025

print("=== HYDRIC GAP CALCULATION WITH LOCATION-SPECIFIC KC (2020-2025) ===\n")

# Load Kc and irrigation data (agreste_2020 + RPG_2023, assumed constant over 2020-2025)
print("Loading Kc and irrigation data for SAFRAN points...")
print("  Kc based on agreste_2020 crop distribution (constant over period)")
kc_data = pd.read_csv('data/agreste/safran_commune_kc.csv')
print(f"Loaded Kc data for {len(kc_data)} SAFRAN points")
print(kc_data[['LAMBX', 'LAMBY', 'avg_kc', 'pct_irrigated', 'pct_cereals', 'pct_prairies']])

# Load SIM data (ETP and P) — covers 2020-2025
print("\nLoading SIM data...")
sim_path = Path("data/sim/QUOT_SIM2_reduced.csv")
df_sim = pd.read_csv(sim_path)
df_sim['DATE'] = pd.to_datetime(df_sim['DATE'], format='%Y%m%d')
print(f"SIM data loaded: {len(df_sim)} records")
print(f"Date range: {df_sim['DATE'].min()} to {df_sim['DATE'].max()}")

# Keep only years in YEARS range
df_sim = df_sim[df_sim['DATE'].dt.year.isin(YEARS)]
print(f"Filtered to {YEARS.start}-{YEARS.stop - 1}: {len(df_sim)} records")

# Check coverage per year
for y in YEARS:
    n = (df_sim['DATE'].dt.year == y).sum()
    print(f"  {y}: {n} records" + (" ⚠ MISSING DATA" if n == 0 else ""))

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

# Index SIM data by (LAMBX, LAMBY) for fast lookup
print("\nIndexing SIM data...")
df_sim = df_sim.sort_values(['LAMBX', 'LAMBY', 'DATE']).reset_index(drop=True)
sim_grouped = df_sim.groupby(['LAMBX', 'LAMBY'])

# Vectorized water balance for one point's data (numpy arrays)
def compute_balance(pre, etp, kc, ru_max, years):
    n = len(pre)
    stock_arr = np.empty(n, dtype=np.float32)
    gap_arr = np.empty(n, dtype=np.float32)
    stock = ru_max
    cur_year = -1
    for i in range(n):
        if years[i] != cur_year:
            stock = ru_max
            cur_year = years[i]
        stock = stock + pre[i] - etp[i] * kc
        if stock > ru_max:
            stock = ru_max
        if stock < 0:
            gap_arr[i] = -stock
            stock = 0.0
        else:
            gap_arr[i] = 0.0
        stock_arr[i] = stock
    return stock_arr, gap_arr

# Stream results to CSV in chunks to avoid OOM
output_path = Path("data/gap_results_with_kc.csv")
output_path.unlink(missing_ok=True)
FLUSH_EVERY = 500  # points per chunk
total_records = 0
header_written = False
buf = []

print(f"\nCalculating water balance for each point ({YEARS.start}-{YEARS.stop - 1})...")
print(f"  Streaming to {output_path} every {FLUSH_EVERY} points\n")

for idx, point_row in tqdm(gdf_joined.iterrows(), total=len(gdf_joined)):
    lambx, lamby = point_row['LAMBX'], point_row['LAMBY']
    ru_max = float(point_row['RU_mm'])
    kc = float(point_row['avg_kc'])

    try:
        point_data = sim_grouped.get_group((lambx, lamby))
    except KeyError:
        continue

    dates = point_data['DATE'].values
    pre = point_data['PRE'].values.astype(np.float64)
    etp_vals = point_data['ETP'].values.astype(np.float64)
    years_arr = pd.DatetimeIndex(dates).year.values

    stock_arr, gap_arr = compute_balance(pre, etp_vals, kc, ru_max, years_arr)

    n = len(dates)
    chunk = pd.DataFrame({
        'point': f"({lambx},{lamby})",
        'LAMBX': lambx,
        'LAMBY': lamby,
        'day': dates,
        'P': np.round(pre, 1),
        'ETP': np.round(etp_vals, 1),
        'Kc': round(kc, 3),
        'Stock': np.round(stock_arr, 1),
        'Gap': np.round(gap_arr, 1),
        'RU_max': ru_max,
        'pct_irrigated': round(float(point_row['pct_irrigated']), 1),
        'pct_cereals': round(float(point_row['pct_cereals']), 1),
        'pct_prairies': round(float(point_row['pct_prairies']), 1),
        'pct_permanent': round(float(point_row['pct_permanent']), 1),
        'pct_vineyards': round(float(point_row['pct_vineyards']), 1),
    })
    buf.append(chunk)
    total_records += n

    # Flush buffer to disk periodically
    if len(buf) >= FLUSH_EVERY:
        batch = pd.concat(buf, ignore_index=True)
        batch.to_csv(output_path, mode='a', index=False, header=not header_written)
        header_written = True
        buf.clear()

# Flush remaining
if buf:
    batch = pd.concat(buf, ignore_index=True)
    batch.to_csv(output_path, mode='a', index=False, header=not header_written)
    buf.clear()

print(f"\n=== RESULTS SAVED ===")
print(f"Output file: {output_path}")
print(f"Total records: {total_records}")

# Per-year summary from file (read only small agg, not full DF)
print("\n=== SUMMARY STATISTICS (per year) ===")
for chunk in pd.read_csv(output_path, usecols=['day', 'point', 'Gap', 'P', 'ETP'], chunksize=500_000):
    chunk['year'] = pd.to_datetime(chunk['day']).dt.year
    for y, grp in chunk.groupby('year'):
        print(f"  {y}: {len(grp)} rows, Mean Gap={grp['Gap'].mean():.1f}, Max Gap={grp['Gap'].max():.1f}")

print("\n=== PROCESSING COMPLETE ===")
