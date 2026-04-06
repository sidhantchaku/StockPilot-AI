# StockPilot AI

StockPilot AI is my end-to-end inventory intelligence project for multi-location retail/ecommerce operations.
I built it to solve a practical problem: teams usually have inventory data, but not a fast system for forecasting demand, identifying deadstock, and deciding transfer/restock actions.

## Why I Built This

Most inventory teams operate in spreadsheets and disconnected tools. I wanted one application that can:

- ingest raw inventory data from multiple sources,
- clean and map it quickly,
- run demand and deadstock analysis,
- generate actionable transfer/restock decisions,
- and keep the workflow collaborative with role-based access.

## Core Product Capabilities

### 1) Inventory Command Center
- Live dashboard with key KPIs (stock value, deadstock risk, area-level insights).
- Area and trend views for quick operational monitoring.

### 2) Forecasting Engine
- Time-series demand forecasting using Prophet.
- Forecast visualizations and demand signals for planning.

### 3) Deadstock & Restock Intelligence
- Deadstock detection based on aging and movement patterns.
- Restock recommendations with reorder logic and thresholds.

### 4) Last-Mile + Transfer Optimization
- Inter-location transfer planning based on demand/supply imbalance.
- Route-aware calculations (distance-aware transfer logic).

### 5) Workspace + Role-Based Access
- Authenticated login with role model (`ops`, `manager`, `admin`).
- Workspace-scoped data and actions.
- Admin user management directly inside the app.

## Data Inputs Supported

- File upload (`.csv`, `.xlsx`)
- Saved workspace snapshots
- Shopify
- WooCommerce
- Google Sheets
- ERP API
- ERP CSV endpoint

## Persistence Layer

Application data is persisted for:

- uploaded datasets,
- column mappings,
- generated plans,
- and user feedback.

Supported DB backends:

- Postgres via `DATABASE_URL` (recommended)
- SQLite fallback for quick demos

Note:
- On Streamlit Cloud, if `DATABASE_URL` is missing/invalid, the app falls back to `/tmp/stockpilot.db` so it remains bootable.
- `/tmp` storage is temporary and not durable across restarts.

## Tech Stack

- **App**: Streamlit
- **Data/Compute**: pandas, NumPy-style transforms, Plotly
- **Forecasting**: Prophet
- **DB/Persistence**: SQLAlchemy (SQLite/Postgres)
- **Integrations**: requests-based connectors (Shopify/WooCommerce/ERP/Sheets)
- **Testing**: pytest unit tests for core forecast/transfer logic
- **CI**: GitHub Actions

## What I Added In This Upgrade

This release includes a major product and engineering upgrade:

- full UI rebrand to **StockPilot AI**,
- persistent storage layer (datasets/mappings/plans/feedback),
- direct external integrations (Shopify, WooCommerce, Google Sheets, ERP),
- authentication + roles + workspace-aware behavior,
- unit tests for core logic,
- CI pipeline via GitHub Actions,
- Docker + Cloud Run/Cloud SQL deployment assets,
- Streamlit Community Cloud deployment setup and runtime fixes.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app2.py
```

## Streamlit Cloud Deployment

Use:

- **Repository**: `ArpanNarula/StockPilot-AI`
- **Branch**: `main`
- **Main file path**: `app2.py`

Set secret:

```toml
DATABASE_URL = "postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME"
```

## Demo Users

- `admin / admin123`
- `manager / manager123`
- `ops / ops123`

(For production/demo interviews, rotate these credentials.)
