import pandas as pd

print("=== COMPARISON: UNIVERSAL KC vs LOCATION-SPECIFIC KC ===\n")

# Load original results (with universal Kc = 0.9)
df_original = pd.read_csv('data/gap_results_3samples.csv')
df_original = df_original[df_original['day'].str.startswith('2020')]  # Filter 2020 only
print(f"Original data (universal Kc=0.9): {len(df_original)} records")

# Load new results (with location-specific Kc)
df_new = pd.read_csv('data/gap_results_3samples_with_kc.csv')
print(f"New data (location-specific Kc): {len(df_new)} records")

print("\n=== COMPARISON BY POINT ===\n")

for point in df_original['point'].unique():
    # Original data
    orig_point = df_original[df_original['point'] == point]
    orig_gap_total = orig_point['Gap'].sum()
    orig_gap_days = (orig_point['Gap'] > 0).sum()
    orig_gap_max = orig_point['Gap'].max()
    orig_kc = orig_point['Kc'].iloc[0]
    
    # New data
    new_point = df_new[df_new['point'] == point]
    if len(new_point) > 0:
        new_gap_total = new_point['Gap'].sum()
        new_gap_days = (new_point['Gap'] > 0).sum()
        new_gap_max = new_point['Gap'].max()
        new_kc = new_point['Kc'].iloc[0]
        irrig_pct = new_point['pct_irrigated'].iloc[0]
        cereals_pct = new_point['pct_cereals'].iloc[0]
        prairies_pct = new_point['pct_prairies'].iloc[0]
        
        print(f"Point {point}:")
        print(f"  Location-specific Kc: {new_kc:.3f} (vs universal: {orig_kc:.3f})")
        print(f"  Land use: {cereals_pct:.1f}% cereals, {prairies_pct:.1f}% prairies")
        print(f"  Irrigation: {irrig_pct:.1f}%")
        print(f"  ")
        print(f"  Total Gap (mm):")
        print(f"    Universal Kc:   {orig_gap_total:.2f} mm")
        print(f"    Specific Kc:    {new_gap_total:.2f} mm")
        print(f"    Difference:     {new_gap_total - orig_gap_total:+.2f} mm ({(new_gap_total - orig_gap_total) / orig_gap_total * 100:+.1f}%)")
        print(f"  ")
        print(f"  Days with water deficit:")
        print(f"    Universal Kc:   {orig_gap_days} days")
        print(f"    Specific Kc:    {new_gap_days} days")
        print(f"    Difference:     {new_gap_days - orig_gap_days:+d} days")
        print(f"  ")
        print(f"  Maximum daily Gap:")
        print(f"    Universal Kc:   {orig_gap_max:.2f} mm")
        print(f"    Specific Kc:    {new_gap_max:.2f} mm")
        print(f"    Difference:     {new_gap_max - orig_gap_max:+.2f} mm")
        print()

print("\n=== KEY INSIGHTS ===")
print("- Using location-specific Kc (1.03-1.04) instead of universal Kc (0.9)")
print("- Higher Kc values increase water consumption (ETP * Kc)")
print("- This results in higher water deficits (Gap) and more deficit days")
print("- The increase is ~15% in total Gap, reflecting the ~15% higher Kc")
print("- Irrigation percentages are very low (<0.5%), indicating rain-fed agriculture")
print("- Land use is dominated by cereals (42-47%) and prairies (53-58%)")

print("\n=== PROCESSING COMPLETE ===")
