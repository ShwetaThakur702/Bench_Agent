# Bench Agent

A hybrid rule-based + AI system for IT services bench management. Tracks deployable (non-billable) employees, forecasts upcoming project releases, fires threshold alerts by org slice, and advises hiring freezes when supply exceeds demand. Advisory only — the agent never enforces decisions.

---

## Project Overview

The Bench Agent runs four business rules in sequence:

| Rule | Name | Description |
|------|------|-------------|
| **R1** | Bench Snapshot | Computes current headcount KPIs — total deployable bench, aging distribution, location split, status breakdown (available / proposed / NAFD / allocated) |
| **R2** | Release Forecast | Builds a 91-day daily forecast of bench additions based on confirmed and projected project release dates |
| **R3** | Threshold Alerts | Compares current bench count per org slice against configured thresholds; fires CRITICAL / HIGH / MEDIUM alerts on breach |
| **R4** | Hiring Freeze Advisory | Computes supply vs open demand per skill; recommends hiring freezes where supply surplus exists; enriches recommendations with an LLM-generated narrative via LangGraph |

All outputs are advisory. The system produces an Excel report, persists results to PostgreSQL, and exposes a REST API consumed by a React dashboard.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.9+ |
| Data processing | pandas, openpyxl |
| AI orchestration | LangGraph + LangChain |
| LLM | GPT via OpenRouter (`openai/gpt-5-mini`) |
| REST API | FastAPI + uvicorn |
| Database | PostgreSQL 16 + psycopg2 |
| Frontend | React 18 + TypeScript + Vite |
| Charts | Recharts |
| HTTP client | Axios |

---

## Setup Instructions

### Prerequisites

- Python 3.9+
- Node 18+ and npm
- PostgreSQL 16

### Install

```bash
# 1. Clone the repository
git clone <repo-url>
cd bench_agent

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Open .env and fill in your OpenRouter API key and POSTGRES_URL
```

### Database Setup

#### macOS (Homebrew)

```bash
# 1. Install PostgreSQL 16
brew install postgresql@16

# 2. Start the service
brew services start postgresql@16

# 3. Add to PATH
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc

# 4. Create the database
createdb bench_agent

# 5. Apply the schema
psql -d bench_agent -f schema.sql

# 6. Verify tables were created
psql -d bench_agent -c "\dt"
# Should show: bench_snapshots, bench_forecasts, bench_alerts
```

#### Linux (Ubuntu / Debian)

```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo -u postgres createdb bench_agent
sudo -u postgres psql -d bench_agent -f schema.sql
```

#### Windows

Download the installer from https://www.postgresql.org/download/windows/

After installation, open pgAdmin or the psql shell and run:

```sql
CREATE DATABASE bench_agent;
```

Then apply the schema:

```bash
psql -U postgres -d bench_agent -f schema.sql
```

#### POSTGRES_URL in `.env`

```bash
# macOS / Linux (no password, socket connection)
POSTGRES_URL=postgresql://localhost/bench_agent

# Windows
POSTGRES_URL=postgresql://postgres:yourpassword@localhost/bench_agent
```

### Frontend

```bash
cd ui
npm install
```

---

## Running the Agent

Open two terminals from the project root.

**Terminal 1 — FastAPI server:**

```bash
python3 -m uvicorn api:app --reload
# Serves on http://localhost:8000
# Runs the full ingestion pipeline on startup and caches results in memory
```

**Terminal 2 — React dashboard:**

```bash
cd ui
npm run dev
# Serves on http://localhost:5173
```

Open **http://localhost:5173** in your browser.

The dashboard banner shows **"Live data from API"** when the FastAPI server is reachable, and falls back to **"API Offline — Static Preview"** with hardcoded sample data if it is not.

**To run the full pipeline manually (Excel + DB output, no HTTP server):**

```bash
MOCK_LLM=true python3 -m agents.bench_agent.agent
# Output written to output/BA_Dashboard_YYYYMMDD.xlsx
# Results persisted to PostgreSQL
```

Set `MOCK_LLM=false` in `.env` (or unset the env override) to use the real LLM.

---

## Running Tests

```bash
pytest -v
```

The test suite uses session-scoped fixtures — the pipeline runs once per session and all 52 tests share the cached DataFrames.

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_ingestion.py` | 8 | File loads, row counts, artifact drop, null Emplid rejection |
| `tests/test_preprocessing.py` | 8 | Column count 113→105, date parsing, dropped columns |
| `tests/test_exclusion_filters.py` | 10 | Tuple shape, 80+920=1000 split, all 6 exclusion conditions |
| `tests/test_feature_engineering.py` | 8 | 6 derived columns, confidence values, list types, bucket names |
| `tests/test_rules.py` | 18 | R1 KPIs, R2 FC2 compliance, R3 breach detection, R4 TC2 + surplus sign |

---

## Project Structure

```
bench_agent/
├── api.py                     # FastAPI REST server (5 endpoints)
├── schema.sql                 # PostgreSQL DDL — 3 tables
├── requirements.txt
├── .env                       # Local secrets (not committed)
├── .env.example               # Placeholder template (committed)
├── plan.md                    # Implementation blueprint
│
├── agents/
│   └── bench_agent/
│       ├── agent.py           # LangGraph StateGraph — 10-node pipeline
│       └── prompts.py         # LLM prompt templates
│
├── pipeline/
│   ├── ingestion.py           # Loads all 4 source Excel files
│   ├── preprocessing.py       # Type casting, column drops
│   ├── exclusion_filters.py   # Deployable bench isolation
│   ├── feature_engineering.py # 6 derived columns
│   ├── r1_bench_snapshot.py   # Headcount KPIs
│   ├── r2_forecast.py         # 91-day daily forecast
│   ├── r3_threshold.py        # Org-slice breach alerts
│   ├── r4_hiring_freeze.py    # Skill-level freeze advisory
│   └── persistence.py         # psycopg2 DB writes (no ORM)
│
├── output/
│   └── excel_writer.py        # Writes BA_Dashboard_YYYYMMDD.xlsx
│
├── ui/                        # React + TypeScript frontend
│   ├── src/
│   │   ├── App.tsx            # Tab navigation + data fetching
│   │   ├── types.ts           # TypeScript interfaces
│   │   ├── sampleData.ts      # Fallback data (API offline)
│   │   ├── api.ts             # Axios fetch functions
│   │   └── components/        # Header, TabNav, BenchSummary, Forecast,
│   │                          # ThresholdAlerts, HiringFreeze
│   └── package.json
│
├── data/                      # Source Excel files (read-only, never modified)
│   ├── RIS_Synthetic.xlsx
│   ├── Skill_Data_Synthetic.xlsx
│   ├── SO_Ageing_Synthetic.xlsx
│   └── Bench_Threshold.xlsx
│
└── tests/
    ├── conftest.py            # Session-scoped pipeline fixtures
    ├── test_ingestion.py
    ├── test_preprocessing.py
    ├── test_exclusion_filters.py
    ├── test_feature_engineering.py
    └── test_rules.py
```

---

## Hard Constraints Implemented

| Constraint | Description |
|------------|-------------|
| **TC2** | LLM receives only aggregated skill-level statistics — no Emplid, no employee names, no individual rows. Verified by `test_r4_no_pii_columns`. |
| **TC3** | Exclusion filters run before any headcount computation. The LangGraph node order enforces this: `apply_exclusions` → `engineer_features` → `run_r1`. |
| **TC4** | Threshold values are loaded from `data/Bench_Threshold.xlsx` at runtime. No thresholds are hardcoded anywhere in the pipeline. |
| **TC5** | The skill column `Skiil` (intentionally misspelled in source data) is never renamed. All pipeline code references it as `"Skiil"`. Verified by `test_skiil_column_preserved`. |
| **FC2** | Every forecast row has `forecast_confidence_band` populated — `"HIGH"` when only confirmed releases, `"MIXED"` otherwise. Verified by `test_r2_forecast_confidence_band_no_nulls`. |
| **FC3** | All null fields in Excel output are replaced with `"N/A"` — no blank cells. Enforced in `output/excel_writer.py`. |

---

## Known Limitations

**Exclusion filters pending business validation:**

| Filter | Status | Issue |
|--------|--------|-------|
| `CAO Status == 'Old'` | Skipped | The `CAO` column contains client account names (955/1000 non-null), not a status flag. Correct exclusion logic awaiting mentor confirmation. |
| `BNH / BNHP projects` | Skipped | Covers 68% of the synthetic dataset. Likely a data artifact in synthetic data — excluding would reduce deployable bench to ~25 rows. Pending validation. |
| `OC column` | Skipped | Column contains Emplid cross-references, not a binary flag. Business rule unclear. |

**Data:**

- Synthetic dataset produces **80 deployable bench rows** after confirmed exclusion filters. Production data may yield different counts.
- 9 of 80 bench rows are `UNMAPPED` (no matching org slice in threshold config). These are client account department IDs not covered by the current threshold file.
- `Confirm Release Period` is 100% null in the synthetic dataset and is excluded from all computations.
