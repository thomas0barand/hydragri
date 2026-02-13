import pandas as pd
import numpy as np
from pathlib import Path
from scipy.spatial import cKDTree

print("=== LINKING COMMUNES TO SAFRAN POINTS ===\n")

# Agreste 2020 and RPG 2023 are considered constant over the 2020-2025 period
print("Agreste/RPG data assumed constant for 2020-2025\n")

# Typical Kc values for different crop types (mid-season values)
KC_VALUES = {
    'cereals': 1.15,      # Céréales et oléo-protéagineux
    'permanent': 0.95,     # Cultures permanentes (arbres fruitiers)
    'prairies': 0.95,      # Prairies
    'vineyards': 0.70      # Vignes
}

# Load commune geographic data - only needed columns
print("Loading commune data...")
commune_geo = pd.read_csv('data/agreste/20230823-communes-departement-region.csv',
                          usecols=['code_commune_INSEE', 'latitude', 'longitude', 'nom_commune'])
print(f"Loaded {len(commune_geo)} communes")

# Load agreste agricultural data - only needed columns to reduce memory
print("Loading agreste agricultural data...")
needed_cols = ['Code', 'SAU en 2020', 
               'Part de la superficie irriguée dans la SAU, 2020',
               'Part des céréales et oléo-protéagineux dans la SAU, 2020',
               'Part des cultures permanentes dans la SAU, 2020',
               'Part des prairies dans la SAU, 2020',
               'Part des vignes dans la SAU, 2020']
agreste = pd.read_csv('data/agreste/agreste_2020.csv', sep=';', skiprows=2, usecols=needed_cols, low_memory=False)
# Clean column names
agreste.columns = agreste.columns.str.strip()
print(f"Loaded {len(agreste)} agricultural records")

# Parse the code column (commune code)
agreste['code_commune'] = agreste['Code'].astype(str).str.zfill(5)

# Merge with commune coordinates
print("\nMerging agricultural data with commune coordinates...")
agreste_geo = agreste.merge(
    commune_geo[['code_commune_INSEE', 'latitude', 'longitude', 'nom_commune']],
    left_on='code_commune',
    right_on='code_commune_INSEE',
    how='left'
)

# Remove rows without coordinates
agreste_geo = agreste_geo.dropna(subset=['latitude', 'longitude'])
print(f"Communes with coordinates: {len(agreste_geo)}")

sim_path = Path("data/sim/QUOT_SIM2_reduced.csv")
df_sim = pd.read_csv(sim_path)
safran_points = df_sim[['LAMBX', 'LAMBY']].drop_duplicates().reset_index(drop=True)
print(f"Unique SAFRAN points: {len(safran_points)}")

# Convert SAFRAN coordinates from Lambert II étendu (hectometers) to WGS84 (lat/lon)
# SAFRAN uses Lambert II étendu (EPSG:27582), coordinates are in hectometers (x100 = meters)
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:27582", "EPSG:4326", always_xy=True)

safran_latlon = []
for idx, row in safran_points.iterrows():
    # Convert from hectometers to meters
    x_m = row['LAMBX'] * 100
    y_m = row['LAMBY'] * 100
    lon, lat = transformer.transform(x_m, y_m)
    safran_latlon.append({'LAMBX': row['LAMBX'], 'LAMBY': row['LAMBY'], 'lat': lat, 'lon': lon})
    print(f"SAFRAN point ({row['LAMBX']}, {row['LAMBY']}) = ({lat:.4f}°N, {lon:.4f}°E)")

safran_df = pd.DataFrame(safran_latlon)

# Find nearest communes for each SAFRAN point using KDTree (radius search)
print("\nFinding communes within 10km radius of each SAFRAN point...")

# Build KDTree for communes
commune_coords = agreste_geo[['latitude', 'longitude']].values
commune_tree = cKDTree(commune_coords)

# For each SAFRAN point, find all communes within radius
radius_km = 10
radius_deg = radius_km / 111  # Approximate: 1 degree ≈ 111 km

safran_commune_links = []

for idx, safran in safran_df.iterrows():
    safran_coord = np.array([safran['lat'], safran['lon']])
    
    # Find all communes within radius
    indices = commune_tree.query_ball_point(safran_coord, radius_deg)
    
    print(f"\nSAFRAN point ({safran['LAMBX']}, {safran['LAMBY']}): {len(indices)} communes within {radius_km}km")
    
    if len(indices) == 0:
        print(f"  WARNING: No communes found within {radius_km}km!")
        continue
    
    # Get communes data
    nearby_communes = agreste_geo.iloc[indices].copy()
    
    # Calculate distance for each commune
    nearby_communes['distance_km'] = nearby_communes.apply(
        lambda row: np.sqrt((row['latitude'] - safran['lat'])**2 + 
                           (row['longitude'] - safran['lon'])**2) * 111,
        axis=1
    )
    
    # Parse agricultural data (handle N/A values)
    def parse_value(val):
        if pd.isna(val) or val == 'N/A' or val == '':
            return 0.0
        try:
            return float(val)
        except:
            return 0.0
    
    # Extract crop percentages
    nearby_communes['sau'] = nearby_communes['SAU en 2020'].apply(parse_value)
    nearby_communes['pct_irrigated'] = nearby_communes['Part de la superficie irriguée dans la SAU, 2020'].apply(parse_value)
    nearby_communes['pct_cereals'] = nearby_communes['Part des céréales et oléo-protéagineux dans la SAU, 2020'].apply(parse_value)
    nearby_communes['pct_permanent'] = nearby_communes['Part des cultures permanentes dans la SAU, 2020'].apply(parse_value)
    nearby_communes['pct_prairies'] = nearby_communes['Part des prairies dans la SAU, 2020'].apply(parse_value)
    nearby_communes['pct_vineyards'] = nearby_communes['Part des vignes dans la SAU, 2020'].apply(parse_value)
    
    # Filter communes with SAU > 0
    nearby_communes = nearby_communes[nearby_communes['sau'] > 0]
    
    if len(nearby_communes) == 0:
        print(f"  WARNING: No communes with agricultural data!")
        continue
    
    # Calculate weighted average Kc based on crop distribution and SAU area
    # Weight = SAU area (larger communes have more influence)
    total_sau = nearby_communes['sau'].sum()
    
    # Calculate weighted crop percentages
    weighted_cereals = (nearby_communes['pct_cereals'] * nearby_communes['sau']).sum() / total_sau
    weighted_permanent = (nearby_communes['pct_permanent'] * nearby_communes['sau']).sum() / total_sau
    weighted_prairies = (nearby_communes['pct_prairies'] * nearby_communes['sau']).sum() / total_sau
    weighted_vineyards = (nearby_communes['pct_vineyards'] * nearby_communes['sau']).sum() / total_sau
    weighted_irrigated = (nearby_communes['pct_irrigated'] * nearby_communes['sau']).sum() / total_sau
    
    # Normalize percentages (they might not sum to 100%)
    total_pct = weighted_cereals + weighted_permanent + weighted_prairies + weighted_vineyards
    if total_pct > 0:
        weighted_cereals = weighted_cereals / total_pct * 100
        weighted_permanent = weighted_permanent / total_pct * 100
        weighted_prairies = weighted_prairies / total_pct * 100
        weighted_vineyards = weighted_vineyards / total_pct * 100
    
    # Calculate average Kc as weighted average of crop-specific Kc
    avg_kc = (
        weighted_cereals / 100 * KC_VALUES['cereals'] +
        weighted_permanent / 100 * KC_VALUES['permanent'] +
        weighted_prairies / 100 * KC_VALUES['prairies'] +
        weighted_vineyards / 100 * KC_VALUES['vineyards']
    )
    
    print(f"  Total SAU: {total_sau:.0f} ha")
    print(f"  Crop distribution (weighted by SAU):")
    print(f"    Cereals: {weighted_cereals:.1f}% (Kc={KC_VALUES['cereals']})")
    print(f"    Permanent cultures: {weighted_permanent:.1f}% (Kc={KC_VALUES['permanent']})")
    print(f"    Prairies: {weighted_prairies:.1f}% (Kc={KC_VALUES['prairies']})")
    print(f"    Vineyards: {weighted_vineyards:.1f}% (Kc={KC_VALUES['vineyards']})")
    print(f"  Irrigated surface: {weighted_irrigated:.1f}%")
    print(f"  Calculated average Kc: {avg_kc:.3f}")
    
    # Quantize data to reduce file size
    safran_commune_links.append({
        'LAMBX': safran['LAMBX'],
        'LAMBY': safran['LAMBY'],
        'lat': round(safran['lat'], 4),
        'lon': round(safran['lon'], 4),
        'n_communes': len(nearby_communes),
        'total_sau': round(total_sau, 0),
        'pct_cereals': round(weighted_cereals, 1),
        'pct_permanent': round(weighted_permanent, 1),
        'pct_prairies': round(weighted_prairies, 1),
        'pct_vineyards': round(weighted_vineyards, 1),
        'pct_irrigated': round(weighted_irrigated, 1),
        'avg_kc': round(avg_kc, 3)
    })

# Create DataFrame with results
df_links = pd.DataFrame(safran_commune_links)

# Save to CSV
output_path = 'data/agreste/safran_commune_kc.csv'
df_links.to_csv(output_path, index=False)
print(f"\n=== RESULTS SAVED ===")
print(f"Output file: {output_path}")
print(f"SAFRAN points processed: {len(df_links)}")

print("\n=== SUMMARY ===")
if len(df_links) > 0:
    print(df_links[['LAMBX', 'LAMBY', 'n_communes', 'total_sau', 'pct_irrigated', 'avg_kc']].to_string(index=False))
else:
    print("No SAFRAN points were successfully processed!")

print("\n=== PROCESSING COMPLETE ===")
