"""
One-time script to convert webpage 10 Excel files into JSON files
for the R3 interactive grid emission charts in the frontend.

Output: one JSON file per state+gas combination (12 total)
Format: { "scenarios": { "Scenario Name": [{ "date": "Jan 2025", "value": 2.88 }, ...] } }
"""

import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- Paths ---
INPUT_DIR = r"C:\Users\nenoa\OneDrive\Desktop\CyberlawAndPolicy\20250611_UI Datasets, Map Files, and Logos\20250611_UI Datasets, Map Files, and Logos\UI code\webpage 10\Abstract calculation"
OUTPUT_DIR = r"C:\Users\nenoa\OneDrive\Desktop\CyberlawAndPolicy\Emission-website 3\Emission-website\src\assets\r3data"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def excel_serial_to_date(serial):
    """Convert Excel serial date number to a readable date string."""
    try:
        base = datetime(1899, 12, 30)
        return (base + timedelta(days=int(serial))).strftime("%b %Y")
    except Exception:
        return str(serial)

def clean_scenario_name(sheet_name):
    """Extract clean scenario name from sheet name like 'Scenario 1 _ Mid-case Scenario'."""
    parts = sheet_name.split(" _ ", 1)
    return parts[1].strip() if len(parts) > 1 else sheet_name.strip()

files = [f for f in os.listdir(INPUT_DIR) if f.startswith("plotting_data_") and f.endswith(".xlsx")]

for filename in sorted(files):
    # e.g. plotting_data_GA_CO2.xlsx -> GA_CO2
    base = filename.replace("plotting_data_", "").replace(".xlsx", "")
    filepath = os.path.join(INPUT_DIR, filename)

    print(f"Processing {filename}...")

    xf = pd.ExcelFile(filepath)
    result = {"scenarios": {}}

    for sheet_name in xf.sheet_names:
        df = xf.parse(sheet_name)

        # Ensure required columns exist
        if "ds" not in df.columns or "adjusted_yhat" not in df.columns:
            print(f"  Skipping sheet '{sheet_name}' - missing columns")
            continue

        scenario_label = clean_scenario_name(sheet_name)

        points = []
        for _, row in df.iterrows():
            try:
                date_str = excel_serial_to_date(row["ds"])
                value = round(float(row["adjusted_yhat"]), 4)
                points.append({"date": date_str, "value": value})
            except Exception:
                continue

        result["scenarios"][scenario_label] = points

    out_path = os.path.join(OUTPUT_DIR, f"{base}.json")
    with open(out_path, "w") as f:
        json.dump(result, f)

    print(f"  -> Wrote {out_path} ({len(result['scenarios'])} scenarios)")

print("\nDone. All JSON files written to:", OUTPUT_DIR)
