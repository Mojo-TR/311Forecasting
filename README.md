# 311 Detector

## Overview

311 Detector is an end-to-end data analytics and forecasting platform built to analyze Houston 311 service requests. The project ingests raw city data, transforms it into analytics ready datasets, and powers interactive dashboards and time-series forecasts to surface trends, bottlenecks, and future demand.

The system is designed with performance and scalability in mind, using precomputed datasets and modular forecasting logic to support fast, reliable visualizations.

---

## Key Capabilities
- **Data Engineering Pipeline**
    - Ingests large, raw 311 service-request files
    - Cleans, normalizes, and enriches records
    - Outputs structured Parquet layers for fast access
- **Interactive Analytics Dashboard**
    - Built with Dash and Plotly
    - Filters by neighborhood, department, division, and category
    - KPI summaries, tables, and trend visualizations
- **Time-Series Forecasting**
    - Monthly volume and severity forecasts using Prophet
    - Citywide and neighborhood-level projections
    - Confidence intervals and rolling trend extensions
    - Reliability checks (minimum history, error thresholds)
- **Performance-First Design**
    - Precomputed forecast and summary tables
    - Avoids heavy computation at request time
    - Modular utilities for reuse and testing

---

## Tech Stack
- **Language:** Python
- **Database:** PostgreSQL
- **Data Processing:** Pandas, NumPy
- **Storage & Caching:** PostgreSQL (system of record), Parquet (precomputed analytics & forecasts)
- **Forecasting:** Prophet
- **Visualization:** Dash, Plotly, Dash Bootstrap Components

---

## Project Structure
```
311Detector/                  # Project root
├── app/
│   ├── assets/               # Static Dash assets
│   ├── pages/                # Dashboard views (multi-page Dash app)
│   ├── utils/                # Data loading, forecasting, shared helpers
│   └── app.py                # Dash application entry point
│
├── csv/                      # Exported CSV outputs (optional / local)
├── data/                     # Raw 311 source files (local-only, ignored)
├── notebooks/                # Exploration and prototyping notebooks
│
├── precompute/               # Precompute pipeline modules
├── precomputed_data/         # Cached analytics & forecast outputs (Parquet)
│
├── precompute.py             # Runs full precompute pipeline
├── refresh_data.py           # Refreshes data and rebuilds outputs
├── README.md
```
---

## Installation
**Python 3.10+ recommended**

```bash
gitclone https://github.com/Mojo-TR/311Forecasting
cd 311Detector
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

```

---

## Running the App
```bash
python app/app.py

```

Open your browser to:

```
http://127.0.0.1:8050

```

---

## Data Notes
- Data is sourced from public Houston 311 service-request records
- Forecasts are built on **monthly aggregates**
- Low-volume or incomplete months are excluded to improve model reliability
- Forecast outputs may differ slightly from raw aggregations due to:
    - Volume thresholds
    - Rolling averages
    - Forecast horizon boundaries

These design choices are intentional and documented to prioritize stability over noise.

---

## Forecasting Approach
- Prophet models with yearly seasonality
- Separate pipelines for:
    - **Volume forecasts** (request counts)
    - **Severity forecasts** (resolution time metrics)
- Reliability flags based on:
    - Minimum historical length
    - Error thresholds (MAPE)
- Rolling trends shown for interpretability only (not model inputs)

---

## Why This Project Matters
This project demonstrates:

- Real-world data engineering on messy public datasets
- Scalable dashboard architecture
- Practical forecasting with uncertainty awareness
- Clear separation between data prep, modeling, and presentation

It’s built to mirror how analytics systems are designed in production—not notebooks.

---

## Notes on Forecast Consistency
Forecast outputs in exploratory notebooks may differ slightly from those shown in the dashboard.

This is intentional.

- Notebooks are used for experimentation, diagnostics, and model iteration
- Dashboards rely on validated, precomputed forecast layers designed for stability
- Dashboard forecasts apply stricter rules, including:
  - Minimum data volume thresholds
  - Removal of incomplete or low-signal months
  - Fixed forecast horizons
  - Reliability checks (e.g., error thresholds)

As a result, notebook forecasts may explore alternative assumptions or include edge cases that are excluded from production dashboards.

In short: notebooks prioritize exploration, dashboards prioritize reliability.

---

## Future Improvements
- Scheduled refresh via cron / task runner
- Model comparison (Prophet vs ARIMA)
- Deployment to cloud hosting
