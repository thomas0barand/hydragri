import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Load results
df = pd.read_csv('data/gap_results.csv')
df['day'] = pd.to_datetime(df['day'])

# Create figure with subplots
fig, axes = plt.subplots(3, 1, figsize=(14, 12))

for idx, point in enumerate(df['point'].unique()):
    point_data = df[df['point'] == point].sort_values('day')
    ax = axes[idx]
    
    # Plot on twin axes
    ax2 = ax.twinx()
    
    # Plot P and ETP as bars
    ax.bar(point_data['day'], point_data['P'], alpha=0.5, label='P (Precipitation)', color='blue', width=1)
    ax.bar(point_data['day'], -point_data['ETP'], alpha=0.5, label='ETP', color='orange', width=1)
    
    # Plot Stock and Gap as lines
    ax2.plot(point_data['day'], point_data['Stock'], label='Stock', color='green', linewidth=2)
    ax2.fill_between(point_data['day'], 0, point_data['Gap'], 
                      where=(point_data['Gap'] > 0), alpha=0.3, 
                      label='Gap (Deficit)', color='red')
    
    # Formatting
    ax.set_ylabel('P / ETP (mm)', fontsize=10)
    ax2.set_ylabel('Stock / Gap (mm)', fontsize=10)
    ax.set_title(f'Water Balance for Point {point}', fontsize=12, fontweight='bold')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3)
    
    # Legends
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)
    
    # Format x-axis
    ax.set_xlabel('Date', fontsize=10)

plt.tight_layout()
plt.savefig('data/gap_visualization.png', dpi=150, bbox_inches='tight')
print("Visualization saved to data/gap_visualization.png")

# Create summary report
print("\n=== WATER BALANCE SUMMARY ===\n")
for point in df['point'].unique():
    point_data = df[df['point'] == point]
    
    print(f"Point: {point}")
    print(f"  Total Precipitation: {point_data['P'].sum():.1f} mm")
    print(f"  Total ETP: {point_data['ETP'].sum():.1f} mm")
    print(f"  Total Water Consumption (ETP*Kc): {(point_data['ETP'] * point_data['Kc']).sum():.1f} mm")
    print(f"  Total Gap: {point_data['Gap'].sum():.1f} mm")
    print(f"  Days with Gap: {(point_data['Gap'] > 0).sum()}")
    print(f"  Max Gap (single day): {point_data['Gap'].max():.2f} mm")
    print(f"  Min Stock: {point_data['Stock'].min():.2f} mm")
    print(f"  Mean Stock: {point_data['Stock'].mean():.2f} mm")
    print()
