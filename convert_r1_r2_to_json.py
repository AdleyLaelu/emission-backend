"""
One-time script to convert webpage 8 (daily) and webpage 9 (annual) Excel files
into JSON files for the R1 and R2 interactive vehicle charts in the frontend.

Output: 8 JSON files (one per city × daily/annual)
Format: { "CO2": { "labels": [...], "unit": "...", "tracts": { "id": [v,...] } }, ... }
"""

import pandas as pd
import json
import os

# --- Paths ---
BASE_DIR = r"C:\Users\nenoa\OneDrive\Desktop\CyberlawAndPolicy\20250611_UI Datasets, Map Files, and Logos\20250611_UI Datasets, Map Files, and Logos\UI code"
WEBPAGE8_DIR = os.path.join(BASE_DIR, "webpage 8", "Data")
WEBPAGE9_DIR = os.path.join(BASE_DIR, "webpage 9", "Data")
OUTPUT_DIR = r"C:\Users\nenoa\OneDrive\Desktop\CyberlawAndPolicy\Emission-website 3\Emission-website\src\assets\r1r2data"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- City mapping: folder name -> output key ---
CITIES = {
    "Georgia":    "GA",
    "California": "CA",
    "Newyork":    "NY",
    "Washington": "WA",
}

# --- Metric mapping: JSON key -> (filename, divisor, unit label) ---
# Divisors from webpage 8.ipynb
METRICS = {
    "CO2":         ("CO2.xlsx",                            1_000_000,   "CO\u2082 (ton)"),
    "NOx":         ("NOx.xlsx",                            1_000,       "NO\u2093 (kg)"),
    "PM2.5B":      ("PM25_Brakewear.xlsx",                 1,           "PM2.5 Brakes (gm)"),
    "PM2.5T":      ("PM25_Tirewear.xlsx",                  1,           "PM2.5 Tires (gm)"),
    "Electricity": ("Electricity.xlsx",                    3_600_000,   "Electricity (MWh)"),
    "Gasoline":    ("Gasoline.xlsx",                       123462.432,  "Gasoline (Gallon)"),
    "Diesel":      ("Diesel.xlsx",                         138451.739,  "Diesel (Gallon)"),
    "Ethanol":     ("Ethanol_(E85).xlsx",                  85729.28,    "Ethanol E85 (Gallon)"),
    "CNG":         ("Compressed_natural_Gas_(CNG).xlsx",   124854.529,  "CNG (GGE)"),
}

# --- California NOx uses divisor=1/gm (different from other cities in notebook) ---
CA_NOX_DIVISOR = (1, "NO\u2093 (gm)")


def read_metric(filepath, divisor, is_r1):
    """
    Read an Excel file with sheets named 'tract=XXXXXXX'.
    R1: columns are hours '1:00' ... '24:00'
    R2: columns are years '2024' ... '2030'
    Returns: (labels list, tracts dict)
    """
    try:
        xf = pd.ExcelFile(filepath)
    except Exception as e:
        print(f"  ERROR reading {filepath}: {e}")
        return None, None

    tracts = {}
    labels = None

    for sheet in xf.sheet_names:
        if not sheet.startswith("tract="):
            continue
        tract_id = sheet.split("=", 1)[1]
        df = xf.parse(sheet)

        if labels is None:
            labels = [str(c) for c in df.columns]

        row = df.iloc[0]
        values = []
        for val in row:
            try:
                v = float(val) / divisor
                values.append(round(v, 6))
            except Exception:
                values.append(None)
        tracts[tract_id] = values

    return labels, tracts


for city_folder, city_key in CITIES.items():
    for page, (data_dir, suffix) in [("R1", (WEBPAGE8_DIR, "R1")), ("R2", (WEBPAGE9_DIR, "R2"))]:
        city_dir = os.path.join(data_dir, city_folder, "UI CSV")
        is_r1 = (page == "R1")

        print(f"\nProcessing {city_key} {page} from {city_dir}...")
        result = {}

        for metric_key, (filename, default_divisor, default_unit) in METRICS.items():
            filepath = os.path.join(city_dir, filename)
            if not os.path.exists(filepath):
                print(f"  SKIP (not found): {filename}")
                continue

            # California NOx special case
            if city_key == "CA" and metric_key == "NOx":
                divisor, unit = CA_NOX_DIVISOR
            else:
                divisor, unit = default_divisor, default_unit

            labels, tracts = read_metric(filepath, divisor, is_r1)
            if labels is None:
                continue

            result[metric_key] = {
                "labels": labels,
                "unit": unit,
                "tracts": tracts,
            }
            print(f"  {metric_key}: {len(tracts)} tracts, {len(labels)} time points")

        out_path = os.path.join(OUTPUT_DIR, f"{city_key}_{page}.json")
        with open(out_path, "w") as f:
            json.dump(result, f)
        print(f"  -> Wrote {out_path}")

print("\nDone. All R1/R2 JSON files written to:", OUTPUT_DIR)
