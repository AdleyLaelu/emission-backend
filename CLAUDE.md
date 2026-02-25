# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start the main server (port 5003)
python run.py

# Start the legacy simple server (port 5000)
python app.py
```

The app auto-initializes the SQLite database (`prediction.db`) and a default `admin`/`admin` user on startup.

## Architecture Overview

There are two Flask applications in this repo:

- **`run.py`** (port 5003) — the primary application. Contains all upload, prediction, scenario, traffic, and admin endpoints. This is what the frontend uses.
- **`app.py`** (port 5000) — a simpler legacy version with only the 5 basic `/predict/<kind>` endpoints and no database integration. Kept for reference.

### ML Model Layer

`models.py` defines `ModifiedNet` — a 5-layer ReLU network (`input→512→256→128→64→1`) used by the main `run.py` prediction pipeline via `load_state_models()`.

`app.py` defines its own separate `MLPRegressor` (2-layer, `input→32→16→1`) and loads models independently. The two files do **not** share model classes.

Pre-trained PyTorch checkpoints live in `models/{STATE}/`:
- `best_model_{STATE}CO2.pth`
- `best_model_{STATE}Energy.pth`
- `best_model_{STATE}NOx.pth`
- `best_model_{STATE}PM25Brake.pth`
- `best_model_{STATE}PM25Tire.pth`

Each state (CA, GA, NY, WA) has slightly different input feature counts (18–20), defined in the `feature_map_all` dict inside `load_state_models()` in `run.py`.

### Input Feature Construction

Features are always constructed in this order: `[normalized_numerics] + [vehicle_type_one_hot (14)] + [fuel_type_one_hot (5)]`

Numeric features differ by emission type:
- CO2, Energy, NOx → `Age` + `Speed` (normalized via `STATS_AS`)
- PM2.5 Brake Wear → `Vehicle Weight` + `Speed` (normalized via `STATS_WS`)
- PM2.5 Tire Wear → `Speed` + `Road Gradient` (normalized via `STATS_SG`)

Normalization is Z-score: `(value - mean) / std`. Stats are hardcoded constants, not loaded from files.

### City → State Routing

All city-aware endpoints use this mapping (defined in `run.py`):
```python
CITY_TO_STATE = {
    "Atlanta": "GA",
    "Los Angeles": "CA", "LosAngeles": "CA",
    "NewYork": "NY",
    "Seattle": "WA"
}
```
Any unmapped city defaults to `"GA"`. A separate case-insensitive version exists inside `predict_consumption`.

### Traffic Processing Pipeline

`traffic_processor.py` is imported by `run.py` at request time (not at startup) to avoid circular imports. It:

1. Reads input Excel from `Combined_sheet_Input_volume/{STATE}/{STATE}_{year}.xlsx` (one sheet per tract)
2. Applies MFD (Macroscopic Fundamental Diagram) modeling using parameters uploaded via the `/upload/traffic_volume` endpoint
3. Writes output Excel to `Combined_sheet_output_speed/{STATE}/{STATE}_{year}.xlsx`

`traffic_plotter.py` reads from the output directory to generate PNG charts. It is also imported at request time.

GA uses a `_solve_for_k_simple` solver for 3 specific tracts; all other state tracts use the `_solve_for_k_mfd` solver (scipy `fsolve`).

### Database

SQLite (`prediction.db`). All tables are created via `init_db()` on startup. The global `GLOBAL_TRANSACTION_ID = "emission-analysis-2025"` is stamped onto all uploaded data for traceability. Every upload endpoint accepts an optional `transaction_id` form field that overrides this default.

Key tables:
- `vehicle_classification_data` — vehicle counts by type/fuel/city
- `traffic_volume_data` — raw traffic metrics
- `projected_traffic_volume` + `projected_traffic_details` — processed traffic projections
- `mfd_params` — MFD parameters (key-value pairs per tract)
- `results` — stored emission outputs

### Postman Collections

Several Postman collections exist for API testing:
- `Emission_Routes.postman_collection.json` — full route coverage
- `postman_collection_ga.json` / `postman_collection_full_ga.json` — GA-specific flows

## Key Conventions

- All `/upload/<type>` endpoints accept either CSV or Excel; format is detected by file extension (`.csv` vs everything else → `pd.read_excel`)
- `save_to_db_safe()` reconciles DataFrame columns against the actual DB schema before inserting — missing columns are filled with `None`, extra columns are dropped
- Models in `run.py` are loaded lazily per-request via `load_state_models(city_name)`, not cached globally (unlike `app.py` which loads at startup)
- The `/predict_emissions` endpoint iterates speeds 0–70 mph (71 points); `/predict_consumption` iterates 0–69 mph (70 points)
