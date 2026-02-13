#!/usr/bin/env python3
"""Export all spatial scale levels to compact JSON files for the D3 visualization."""

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path("data/spatial_scales")
OUT_DIR = Path("data/spatial_scales")
RPG_FILE = Path("data/rpg_2023/RPG2023_sol_climat.csv")
GEO_CODE_FILE = Path("data/codes/geo-code.json")

SCALES = [
    ("level_0", 80),
    ("level_1", 110),
    ("level_2", 150),
    ("level_3", 210),
    ("level_4", 290),
    ("level_5", 410),
    ("level_6", 640),
]


def load_commune_names():
    """Load commune code → name mapping from geo-code.json."""
    with open(GEO_CODE_FILE) as f:
        data = json.load(f)
    return {c["code"]: c["nom"] for c in data["communes"]}


def load_commune_centroids():
    """Compute commune centroids in LAMB coordinates from RPG parcels."""
    sums = defaultdict(lambda: [0.0, 0.0, 0])
    with open(RPG_FILE) as f:
        for row in csv.DictReader(f):
            code = row["com_parc"]
            raw_x, raw_y = row["mf_lambx"], row["mf_lamby"]
            if raw_x in ("NA", "") or raw_y in ("NA", ""):
                continue
            lx, ly = float(raw_x), float(raw_y)
            s = sums[code]
            s[0] += lx
            s[1] += ly
            s[2] += 1
    return {code: (s[0] / s[2], s[1] / s[2]) for code, s in sums.items()}


def find_nearest_commune(x, y, commune_centroids, commune_names):
    """Return the name of the closest commune for each grid point."""
    codes = list(commune_centroids.keys())
    cx = [commune_centroids[c][0] for c in codes]
    cy = [commune_centroids[c][1] for c in codes]

    names = []
    for px, py in zip(x, y):
        best_d = math.inf
        best_code = None
        for j, code in enumerate(codes):
            d = (px - cx[j]) ** 2 + (py - cy[j]) ** 2
            if d < best_d:
                best_d = d
                best_code = code
        names.append(commune_names.get(best_code, best_code))
    return names


def export_level(level, spacing, commune_centroids, commune_names):
    matches = list(DATA_DIR.glob(f"*{level}*.csv"))
    if not matches:
        print(f"  {level}: no CSV found, skipping")
        return None
    src = matches[0]
    print(f"  {level} ({spacing / 10:.0f}km) – reading {src.name} ...")

    rows_by_week = {}
    all_points = set()

    with open(src) as f:
        for row in csv.DictReader(f):
            w = row["week"]
            pt = (float(row["LAMBX"]), float(row["LAMBY"]))
            all_points.add(pt)
            rows_by_week.setdefault(w, {})[pt] = {
                "stock": round(float(row["Stock"]), 2),
                "gap": round(float(row["Gap"]), 2),
                "P": round(float(row["P"]), 2),
                "ETP": round(float(row["ETP"]), 2),
            }

    points = sorted(all_points)
    weeks = sorted(rows_by_week.keys())
    pt_index = {pt: i for i, pt in enumerate(points)}
    n = len(points)

    x = [pt[0] for pt in points]
    y = [pt[1] for pt in points]

    # Find nearest commune for each grid point
    communes = find_nearest_commune(x, y, commune_centroids, commune_names)

    metrics = {"stock": [], "gap": [], "P": [], "ETP": []}
    for w in weeks:
        arrs = {k: [0.0] * n for k in metrics}
        for pt, vals in rows_by_week[w].items():
            i = pt_index[pt]
            for k in metrics:
                arrs[k][i] = vals[k]
        for k in metrics:
            metrics[k].append(arrs[k])

    out = OUT_DIR / f"{level}_weekly.json"
    data = {
        "spacing": spacing,
        "weeks": weeks,
        "x": x,
        "y": y,
        "communes": communes,
        **metrics,
    }
    with open(out, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    size_kb = out.stat().st_size / 1024
    print(f"    → {n} pts, {len(weeks)} weeks, {size_kb:.0f} KB")
    return out


def main():
    print("Loading commune data ...")
    commune_names = load_commune_names()
    commune_centroids = load_commune_centroids()
    print(f"  {len(commune_centroids)} communes with coordinates")

    print("Exporting all scale levels ...")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for level, spacing in SCALES:
        export_level(level, spacing, commune_centroids, commune_names)
    print("Done.")


if __name__ == "__main__":
    main()
