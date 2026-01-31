"""Preprocess RPG, SIM and geo-code data."""
import json
import os
# from tkinter.constants import N
import pandas as pd

CODES_DIR = "data/codes"
GEO_CODE_PATH = "data/codes/geo-code.json"

# RPG sol climat
RPG_INPUT = "data/rpg_2023/RPG2023_sol_climat.csv"
RPG_OUTPUT = "data/rpg_2023/RPG2023_sol_climat_reduced.csv"
RPG_COLUMNS = [
    "id_parcel", "com_parc", "dep_parc", "reg_parc",
    "mf_lambx", "mf_lamby", "mf_maille", "smu_1",
    "part_smu_1", "stu_dom_1",
]

# SIM quotidiennes: stations (LAMBX,LAMBY), DATE, PRENEI, PRELIQ, EVAP, ETP
SIM_DIR = "data/sim"
SIM_INPUT = "data/sim/QUOT_SIM2_previous-2020-202512.csv"
SIM_OUTPUT = "data/sim/QUOT_SIM2_reduced.csv"
SIM_COLUMNS = ["LAMBX", "LAMBY", "DATE", "PRENEI", "PRELIQ", "EVAP", "ETP"]
SIM_N_STATIONS = 10


def process_rpg(dep_filter=None):
    """Keep selected columns from RPG2023_sol_climat.csv. Optionally filter by dep_parc."""
    df = pd.read_csv(RPG_INPUT, usecols=RPG_COLUMNS)
    if dep_filter is not None:
        df = df[df["dep_parc"] == dep_filter]
    df.to_csv(RPG_OUTPUT, index=False)
    return RPG_OUTPUT


def aggregate_geo_codes():
    """Merge regions, departements, communes into one geo-code.json."""
    with open(f"{CODES_DIR}/codes-regions.json") as f:
        regions = json.load(f)
    with open(f"{CODES_DIR}/codes-departement.json") as f:
        departements = json.load(f)
    with open(f"{CODES_DIR}/codes-communes.json") as f:
        communes = json.load(f)
    out = {"regions": regions, "departements": departements, "communes": communes}
    with open(GEO_CODE_PATH, "w") as f:
        json.dump(out, f, ensure_ascii=False)
    return GEO_CODE_PATH


def process_sim(n_stations=SIM_N_STATIONS):
    """Keep ~n_stations (LAMBX,LAMBY), then DATE, PRENEI, PRELIQ, EVAP, ETP. PRE = PRELIQ + PRENEI."""
    df = pd.read_csv(SIM_INPUT, sep=";", usecols=SIM_COLUMNS)
    if n_stations:
        stations = df[["LAMBX", "LAMBY"]].drop_duplicates().head(n_stations)
    else :
        stations = df[["LAMBX", "LAMBY"]].drop_duplicates()
    df = df.merge(stations, on=["LAMBX", "LAMBY"], how="inner")
    df["PRE"] = df["PRELIQ"] + df["PRENEI"]
    df = df.drop(columns=["PRELIQ", "PRENEI"])
    df.to_csv(SIM_OUTPUT, index=False)
    return SIM_OUTPUT


if __name__ == "__main__":
    # process_rpg(dep_filter=69)
    # print(f"{RPG_INPUT}: {os.path.getsize(RPG_INPUT) / 1e6:.1f} MB")
    # print(f"{RPG_OUTPUT}: {os.path.getsize(RPG_OUTPUT) / 1e6:.1f} MB")

    df_input = pd.read_csv(SIM_INPUT, sep=";", usecols=SIM_COLUMNS)
    print(f"# stations input: {len(df_input[['LAMBX', 'LAMBY']].drop_duplicates())}")
    df_output = pd.read_csv(SIM_OUTPUT)
    print(f"# stations output: {len(df_output[['LAMBX', 'LAMBY']].drop_duplicates())}")


    # process_sim(n_stations=False)
    # print(f"{SIM_INPUT}: {os.path.getsize(SIM_INPUT) / 1e6:.1f} MB")
    # print(f"{SIM_OUTPUT}: {os.path.getsize(SIM_OUTPUT) / 1e6:.1f} MB")