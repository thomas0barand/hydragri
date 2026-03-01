#!/usr/bin/env python3
"""Export all spatial scale levels to compact JSON files for the D3 visualization."""

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path("data/spatial_scales")
OUT_DIR = Path("data")
RPG_FILE = Path("data/rpg_2023/RPG2023_sol_climat_reduced.csv")
GEO_CODE_FILE = Path("data/codes/geo-code.json")
COMMUNES_GEO_CSV = Path("data/agreste/20230823-communes-departement-region.csv")

# Grid (LAMBX, LAMBY) same unit as SAFRAN: Lambert II étendu (EPSG:27582), hectometres (×100 = m).
GRID_TO_METERS = 1
MIN_RPG_COMMUNES_FOR_USE = 2000  # below this, RPG likely a single-region subset → use geo CSV

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
    if not RPG_FILE.exists():
        return {}
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


def load_commune_centroids_wgs84():
    """Load commune (lon, lat) and names from geo CSV for nationwide coverage."""
    if not COMMUNES_GEO_CSV.exists():
        return None, None
    centroids = {}
    names = {}
    with open(COMMUNES_GEO_CSV) as f:
        for row in csv.DictReader(f):
            code = row.get("code_commune_INSEE", row.get("code_commune", ""))
            lat = row.get("latitude")
            lon = row.get("longitude")
            nom = row.get("nom_commune", row.get("nom_commune_complet", code))
            if not code or lat in ("", None) or lon in ("", None):
                continue
            try:
                lat_f, lon_f = float(lat), float(lon)
            except ValueError:
                continue
            code = str(code).zfill(5)
            centroids[code] = (lon_f, lat_f)
            names[code] = nom
    return centroids, names


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


def find_nearest_commune_wgs84(lonlat_list, commune_centroids_wgs84, commune_names):
    """Nearest commune in WGS84 (lon, lat). centroids: code -> (lon, lat)."""
    from scipy.spatial import cKDTree
    codes = list(commune_centroids_wgs84.keys())
    coords = [commune_centroids_wgs84[c] for c in codes]
    tree = cKDTree(coords)
    names = []
    for lon, lat in lonlat_list:
        _, idx = tree.query((lon, lat), k=1)
        code = codes[idx]
        names.append(commune_names.get(code, code))
    return names


def export_level(level, spacing, commune_centroids, commune_names, use_wgs84=False, transformer=None):
    matches = list(DATA_DIR.glob(f"*{level}*.csv"))
    if not matches:
        print(f"  {level}: no CSV found, skipping")
        return None
    src = matches[0]
    print(f"  {level} ({spacing / 10:.0f}km) – reading {src.name} ...")

    rows_by_week = {}
    all_points = set()
    pt_region = {}
    pt_code_region = {}

    with open(src) as f:
        reader = csv.DictReader(f)
        for row in reader:
            w = row["week"]
            pt = (float(row["LAMBX"]), float(row["LAMBY"]))
            all_points.add(pt)
            rows_by_week.setdefault(w, {})[pt] = {
                "stock": round(float(row["Stock"]), 2),
                "gap": round(float(row["Gap"]), 2),
                "P": round(float(row["P"]), 2),
                "ETP": round(float(row["ETP"]), 2),
            }
            if "nom_region" in row and pt not in pt_region:
                pt_region[pt] = row["nom_region"].strip() if row["nom_region"] else ""
            if "code_region" in row and pt not in pt_code_region:
                pt_code_region[pt] = str(row["code_region"]).strip() if row["code_region"] else ""

    points = sorted(all_points)
    weeks = sorted(rows_by_week.keys())
    pt_index = {pt: i for i, pt in enumerate(points)}
    n = len(points)

    x = [pt[0] for pt in points]
    y = [pt[1] for pt in points]

    if use_wgs84 and transformer is not None:
        # Grid in Lambert II hectometres → meters → WGS84 (lon, lat)
        lonlat_list = []
        for xi, yi in zip(x, y):
            x_m = xi * 100
            y_m = yi * 100
            lon, lat = transformer.transform(x_m, y_m)
            lonlat_list.append((lon, lat))
        communes = find_nearest_commune_wgs84(lonlat_list, commune_centroids, commune_names)
    else:
        x_m = [xi * GRID_TO_METERS for xi in x]
        y_m = [yi * GRID_TO_METERS for yi in y]
        communes = find_nearest_commune(x_m, y_m, commune_centroids, commune_names)
    nom_region = [pt_region.get(pt, "") for pt in points]
    code_region = [pt_code_region.get(pt, "") for pt in points]

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
        "code_region": code_region,
        "nom_region": nom_region,
        **metrics,
    }
    with open(out, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    size_kb = out.stat().st_size / 1024
    print(f"    → {n} pts, {len(weeks)} weeks, {size_kb:.0f} KB")
    return out


def main():
    print("Loading commune data ...")
    commune_names_geo = load_commune_names()
    commune_centroids_rpg = load_commune_centroids()

    use_wgs84 = False
    transformer = None
    commune_centroids = commune_centroids_rpg
    commune_names = commune_names_geo

    if len(commune_centroids_rpg) < MIN_RPG_COMMUNES_FOR_USE and COMMUNES_GEO_CSV.exists():
        from pyproj import Transformer
        commune_centroids, commune_names = load_commune_centroids_wgs84()
        if commune_centroids:
            use_wgs84 = True
            transformer = Transformer.from_crs("EPSG:27582", "EPSG:4326", always_xy=True)
            print(f"  Using nationwide communes (WGS84): {len(commune_centroids)} communes")
    else:
        print(f"  Using RPG centroids (Lambert): {len(commune_centroids)} communes")

    print("Exporting all scale levels ...")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for level, spacing in SCALES:
        export_level(level, spacing, commune_centroids, commune_names, use_wgs84=use_wgs84, transformer=transformer)
    print("Done.")


if __name__ == "__main__":
    main()
