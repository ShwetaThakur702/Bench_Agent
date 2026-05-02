# Bench Agent (BA) — Hybrid Resource Management Agent

Bench Agent is a hybrid rule-based + AI-powered system for IT services bench management.
It tracks non-billable employees, forecasts project releases, fires threshold alerts, advises
hiring freezes, and generates advisory communications for resource managers.
**Advisory only — the agent never enforces decisions.**

---

## Architecture

```
Excel Data (4 files)
        │
        ▼
Python Pipeline — LangGraph (12 nodes)
  load_data → preprocess → apply_exclusions → engineer_features
  → run_r1 → run_r2 → run_r3 → run_r4_rules → run_r4_llm
  → run_action_advisor → generate_digest → persist_outputs
        │                        │
        ▼                        ▼
PostgreSQL (3 tables)      Excel Output
        │
        ▼
FastAPI REST API (10 endpoints)
        │
        ▼
React 18 Dashboard (6 tabs + Daily Report modal)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Pipeline | Python 3.9+, pandas, LangGraph, LangChain |
| LLM | GPT-5-mini via OpenRouter (`openai/gpt-5-mini`) |
| Database | PostgreSQL 12+ (psycopg2, no ORM) |
| API | FastAPI + Uvicorn |
| Frontend | React 18 + TypeScript + Vite + Recharts |
| Tests | pytest (56 tests, session-scoped fixtures) |

---

## Pipeline Rules

| Rule | Name | Description |
|---|---|---|
| **R1** | Bench Snapshot | Headcount KPIs — total, aging distribution, location split, status breakdown |
| **R2** | Release Forecast | 91-day daily forecast of bench additions from confirmed + projected release dates |
| **R3** | Threshold Alerts | Compares bench count per org slice against configured thresholds; fires CRITICAL/HIGH/MEDIUM alerts |
| **R4** | Hiring Freeze Advisory | Supply vs open demand per skill; freeze recommendations with LLM-generated narratives |
| **Action Advisor** | Prioritised Actions | IMMEDIATE/7-DAY/30-DAY action steps from all rule outputs, including draft HR emails |
| **Daily Digest** | Intelligence Report | Structured daily report with LLM executive summary (aggregate stats only — TC2 compliant) |
| **RM Nudges** | Nudge Emails | Rule-based email drafts to RMs for bench employees >60 days without proposed status |

---

## Quick Start (Clone or ZIP Download)

This section covers everything from a blank machine to a running agent.

### Step 1 — Get the code

**From ZIP:**
```bash
unzip TeamName_Agent06_BA_Submission.zip
cd Bench_Agent-main
```

**From Git:**
```bash
git clone <repo-url>
cd Bench_Agent-main
```

### Step 2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

> Requires Python 3.9 or higher. Run `python3 --version` to check.

### Step 3 — Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
POSTGRES_URL=postgresql://localhost/bench_agent
OPENAI_API_KEY=your-openrouter-key-here
OPENAI_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-5-mini
MOCK_LLM=false
```

**No OpenRouter key?** Set `MOCK_LLM=true` — the agent runs fully without any API calls, using rule-based fallback text everywhere the LLM would be called.

### Step 4 — Set up PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
createdb bench_agent
psql -d bench_agent -f schema.sql
```

**Ubuntu / Debian:**
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo -u postgres createdb bench_agent
sudo -u postgres psql -d bench_agent -f schema.sql
```

**Windows:**
Download the installer from https://www.postgresql.org/download/windows/, then:
```bash
psql -U postgres -c "CREATE DATABASE bench_agent;"
psql -U postgres -d bench_agent -f schema.sql
```

Verify the schema applied:
```bash
psql -d bench_agent -c "\dt"
# Expected: bench_snapshots, bench_forecasts, bench_alerts
```

**PostgreSQL URL formats:**
```bash
# macOS / Linux (local socket, no password)
POSTGRES_URL=postgresql://localhost/bench_agent

# With username/password
POSTGRES_URL=postgresql://postgres:yourpassword@localhost/bench_agent
```

> PostgreSQL is used for persistence only. The pipeline and API work without it — DB failures log a warning and continue.

### Step 5 — Place input data files

All four files must be present in `data/`:

```
data/
├── RIS_Synthetic.xlsx
├── Skill_Data_Synthetic.xlsx
├── SO_Ageing_Synthetic.xlsx
└── Bench_Threshold.xlsx
```

### Step 6 — Build the React frontend

```bash
cd ui
npm install
npm run build
cd ..
```

> This only needs to be done once. The built UI is served by FastAPI at `http://localhost:8000`.

### Step 7 — Run the agent

**Option A — API + Dashboard (recommended):**

Open two terminals from the project root.

```bash
# Terminal 1 — Start FastAPI (runs pipeline on startup)
python3 -m uvicorn api:app --reload
# API at http://localhost:8000
# Dashboard at http://localhost:8000 (served from ui/dist/)
```

```bash
# Terminal 2 — Start React dev server (optional, for hot reload during development)
cd ui && npm run dev
# Dashboard at http://localhost:5173
```

Open `http://localhost:8000` in your browser.

**Option B — Pipeline only (Excel + DB, no HTTP server):**

```bash
MOCK_LLM=true python3 -m agents.bench_agent.agent
# Writes: output/BA_Dashboard_YYYYMMDD.xlsx
# Persists: R1/R2/R3/R4 results to PostgreSQL
```

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Pipeline status, bench count, run date |
| `GET /api/bench/snapshot` | R1 — current bench KPIs and distributions |
| `GET /api/bench/forecast` | R2 — 91-day daily release forecast (`?days=30\|60\|90`) |
| `GET /api/bench/forecast/org-breakdown` | R2 — forecast split by org slice and bucket |
| `GET /api/bench/alerts` | R3 — threshold breach alerts, severity-sorted |
| `GET /api/bench/hiring-freeze` | R4 — skill supply/demand with LLM narratives |
| `GET /api/bench/deployment-matches` | R4 — skill-level bench-to-demand coverage |
| `GET /api/bench/actions` | Action advisor — IMMEDIATE/7-DAY/30-DAY action steps |
| `GET /api/bench/digest` | Daily intelligence digest with LLM executive summary |
| `GET /api/bench/rm-nudges` | RM nudge email drafts for bench employees >60 days |
| `GET /api/bench/download` | Download latest Excel report |

---

## Dashboard Features

| Tab / Feature | What it shows |
|---|---|
| **Bench Summary** | Total headcount, aging buckets, at-risk count, location/CVF charts |
| **Recommended Actions** | IMMEDIATE/7-DAY/30-DAY action cards + RM Nudge emails section |
| **Release Pipeline** | 91-day forecast chart (confirmed vs projected) + org slice breakdown |
| **Threshold Alerts** | Breach table per org slice with severity badges |
| **Hiring Freeze Advisory** | Skill supply/demand table, surplus indicator, LLM narratives, draft HR emails |
| **Deployment Matches** | Skill-level coverage: FULL / PARTIAL / NONE with gap column |
| **Daily Report (button)** | Modal with bench health status, executive summary, top actions, Copy Report |

The dashboard shows **"Live"** when the FastAPI server is reachable, and falls back to static sample data when offline.

---

## Output Files

```
output/BA_Dashboard_YYYYMMDD.xlsx
├── Sheet: BA_Dashboard   — one row per deployable bench employee (enriched)
├── Sheet: BA_Forecast    — 91-day daily forecast
└── Sheet: BA_Alerts      — threshold breaches + hiring freeze advisories
```

---

## Running Tests

```bash
pytest tests/ -v
```

| File | Tests | What it covers |
|---|---|---|
| `tests/test_ingestion.py` | 8 | File loads, row counts, artifact drop, null Emplid rejection |
| `tests/test_preprocessing.py` | 8 | Column drop (113→105), date parsing, numeric casting |
| `tests/test_exclusion_filters.py` | 10 | Tuple shape, 80+920=1000 split, all 6 exclusion conditions |
| `tests/test_feature_engineering.py` | 8 | 6 derived columns, confidence mapping, bucket names |
| `tests/test_rules.py` | 22 | R1 KPIs, R2 FC2 compliance, R3 breach detection, R4 TC2 + surplus sign |

All 56 tests share session-scoped pipeline fixtures — the pipeline runs once per test session.

---

## Project Structure

```
Bench_Agent-main/
├── api.py                      # FastAPI REST server (10 endpoints)
├── schema.sql                  # PostgreSQL DDL — 3 tables
├── requirements.txt
├── .env.example                # Environment variable template
├── .env                        # Local secrets (not committed)
│
├── agents/
│   └── bench_agent/
│       ├── agent.py            # LangGraph StateGraph — 12-node pipeline
│       └── prompts.py          # LLM prompt templates
│
├── pipeline/
│   ├── ingestion.py            # Loads 4 source Excel files
│   ├── preprocessing.py        # Type casting, whitespace strip, column drops
│   ├── exclusion_filters.py    # Deployable bench isolation (6 conditions)
│   ├── feature_engineering.py  # 6 derived columns (release date, confidence, org slice…)
│   ├── r1_bench_snapshot.py    # Headcount KPIs
│   ├── r2_forecast.py          # 91-day daily + org-slice forecast
│   ├── r3_threshold.py         # Org-slice breach alerts
│   ├── r4_hiring_freeze.py     # Skill supply/demand + deployment match
│   ├── action_advisor.py       # IMMEDIATE/7-DAY/30-DAY actions + draft HR emails
│   ├── digest_generator.py     # Daily digest + RM nudge email generator
│   └── persistence.py          # psycopg2 DB writes (non-blocking)
│
├── output/
│   └── excel_writer.py         # Writes BA_Dashboard_YYYYMMDD.xlsx
│
├── ui/
│   └── src/
│       ├── App.tsx             # 6-tab layout, data fetching, digest modal
│       ├── App.css             # Design system — light/dark, animations
│       ├── types.ts            # TypeScript interfaces
│       ├── api.ts              # Axios fetch functions
│       ├── sampleData.ts       # Offline fallback data (no real names)
│       └── components/
│           ├── Header.tsx          # Nav bar + Daily Report button
│           ├── TabNav.tsx          # 6-tab navigation
│           ├── Skeleton.tsx        # Shimmer loading state
│           ├── BenchSummary.tsx    # KPI cards + 3 charts
│           ├── Forecast.tsx        # 91-day area chart + org breakdown
│           ├── ThresholdAlerts.tsx # Expandable breach table
│           ├── HiringFreeze.tsx    # Skill table + HR email drafts
│           ├── DeploymentMatches.tsx # Skill coverage table
│           ├── ActionCards.tsx     # Action cards + RM Nudge emails
│           └── DigestModal.tsx     # Daily Report modal with Copy Report
│
├── data/                       # Source Excel files (read-only)
│   ├── RIS_Synthetic.xlsx
│   ├── Skill_Data_Synthetic.xlsx
│   ├── SO_Ageing_Synthetic.xlsx
│   └── Bench_Threshold.xlsx
│
└── tests/
    ├── conftest.py             # Session-scoped pipeline fixtures
    ├── test_ingestion.py
    ├── test_preprocessing.py
    ├── test_exclusion_filters.py
    ├── test_feature_engineering.py
    └── test_rules.py
```

---

## LLM Configuration

| Variable | Default | Description |
|---|---|---|
| `LLM_MODEL` | `openai/gpt-5-mini` | Model string in OpenRouter format |
| `OPENAI_API_BASE` | `https://openrouter.ai/api/v1` | API base URL |
| `OPENAI_API_KEY` | — | Your OpenRouter key |
| `MOCK_LLM` | `false` | Set `true` to skip all LLM calls |

Change `LLM_MODEL` in `.env` to switch models with no code changes.

**What uses the LLM:**
- R4 hiring freeze narratives (skill-level aggregates only)
- Action advisor draft HR emails (skill-level aggregates only)
- Daily digest executive summary (5 aggregate counts only)

**What never uses the LLM:**
- R1, R2, R3 rule logic (pure Python/pandas)
- RM Nudge email generation (rule-based f-string, no API call)

---

## Data Privacy (TC2 Compliance)

No employee names or Emplids are ever sent to the LLM.
Only aggregated skill-level counts (5 fields) reach the external API.
All rule logic and RM nudge email generation run entirely locally.

The RM column (manager names) appears in nudge email greetings — this is intentional and stays local; it is never sent to any external model.

---

## Hard Constraints

| Constraint | Description |
|---|---|
| **TC2** | LLM receives only aggregated skill-level stats — verified by `test_r4_no_pii_columns` |
| **TC3** | Exclusion filters enforced before any headcount KPI — node order: `apply_exclusions → engineer_features → run_r1` |
| **TC4** | Threshold values loaded from `data/Bench_Threshold.xlsx` at runtime — none hardcoded |
| **TC5** | Source column `Skiil` (misspelled in source data) is never renamed — verified by `test_skiil_column_preserved` |
| **FC2** | Every forecast row has `forecast_confidence_band` populated — `"HIGH"` or `"MIXED"`, never null |
| **FC3** | All null fields in Excel output replaced with `"N/A"` — no blank cells |

---

## Known Limitations

| Item | Status |
|---|---|
| `CAO Status == 'Old'` exclusion | Skipped — `CAO` column contains client account names, not a status flag. Pending mentor confirmation. |
| BNH/BNHP project exclusion | Skipped — covers 68% of synthetic dataset, likely a data artifact. Pending business validation. |
| `OC` column exclusion | Skipped — contains Emplid cross-references, not a binary flag. Business rule unclear. |
| Deployable bench count | 80 rows from synthetic dataset after confirmed filters. Production data will yield different counts. |
| Unmapped org slices | 9 of 80 bench rows are `UNMAPPED` — client account department IDs not covered by current threshold config. |
| `Confirm Release Period` | 100% null in synthetic dataset — excluded from all computations. |
| Forecast accuracy | Depends on accuracy of release date fields in RIS. Mixed-confidence releases add uncertainty. |

---

## Submission

```
TeamName_Agent06_BA_Submission.zip
```

---

## Changelog — Post-Submission Improvements

### Bug Fixes

#### 1. ECONNREFUSED on Frontend Startup
**Problem:** FastAPI's `lifespan` context manager blocked port binding until the LangGraph pipeline finished (LLM calls took 2+ minutes). The frontend received `ECONNREFUSED` for the entire startup window.

**Fix:** Pipeline now runs in a background daemon thread. The server binds to port 8000 immediately on startup.

```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    import threading
    threading.Thread(target=_run_startup_pipeline, daemon=True).start()
    yield
```

#### 2. 500 Errors After Background Thread Fix
**Problem:** `ready=True` was set immediately after data loading but before rule outputs (snapshot, forecast, etc.) were computed. Requests arriving in that window found `ready=True` but `_cache["snapshot"] == None` → `TypeError`.

**Fix:** All cache keys — including `ready=True` — are now set in a single `_cache.update({...})` call at the very end of `_run_startup_pipeline`, after every rule output is computed.

#### 3. "Offline" Badge Stuck Permanently
**Problem:** `App.tsx` `useEffect` ran once on mount; if the backend was starting up, it failed and `offline=True` was set forever with no retry.

**Fix:** On initial load failure, a `/health` poller fires every 5 seconds. Once `data.pipeline_ready` is `true`, it calls `loadLiveData()` and clears the interval.

```tsx
pollRef.current = setInterval(() => {
  axios.get('/health').then(({ data }) => {
    if (data.pipeline_ready) loadLiveData().finally(() => setLoading(false))
  }).catch(() => {})
}, 5000)
```

#### 4. Skill Gap Tab Showing All Zeros
**Problem 1:** Coverage % used `Math.round()` on very small fractions (e.g., 1/80 = 0.0125 → rounds to 0).
**Fix:** Changed to `Math.ceil()` so any non-zero bench count registers as > 0%.

**Problem 2:** The old heatmap read `f?.bench_count` from the hiring-freeze endpoint, which used the `Skiil` primary column. Multi-skill TalentX matches (via `talentx_skills_list`) were counted correctly in deployment-matches but not reflected in the heatmap.
**Fix:** Replaced the heatmap entirely with real data from `/api/bench/deployment-matches`.

---

### New Features

#### 5. Skill Gap Tab — Complete Redesign
The Skill Gap tab was rebuilt from scratch using only real data from `/api/bench/deployment-matches`. The old estimated heatmap is gone.

**New layout (no-scroll design, all critical info visible on screen):**

| Section | Description |
|---|---|
| Sticky filter bar | Skill search input + Grade Band buttons (`All Grades` / `IS Band` / `DT Band` / …). Stays fixed at top while the rest scrolls. |
| Summary cards | Compact inline row: Total skills · Critical Gaps · Partial · Covered |
| Quick nav badges | `🔴 N Critical` `🟡 N Partial` `🟢 N Covered` — clicking pulses the matching column for 900ms |
| Split view (520px) | Left 40%: Coverage bar chart, worst-first, top 20, scrollable. Right 60%: three independently scrollable columns — Critical / Partial / Covered |
| Skill cards | Coloured left border, progress bar, bench/demand/% stats, hover lift effect, click to expand advisory recommendation |
| Empty state | Green success message when Critical Gaps = 0 |

#### 6. Grade Band Filtering on `/api/bench/deployment-matches`
The endpoint now accepts an optional `grade_band` query parameter. When a band is provided, the pipeline recomputes deployment matches on-demand from the filtered bench subset rather than from pre-cached data.

```
GET /api/bench/deployment-matches?grade_band=IS+Band
```

Supported values: `All` (default), `IS Band`, `DT Band`, `DM Band`, `DP Band`, `BC Band`, `LN Band`, `Others`.

A helper `_get_grade_band(grade)` function in `api.py` detects the band from the raw `Grade` string prefix.

#### 7. Excel Download Button in Header
A download arrow button was added to the header bar. It triggers a direct browser download of the latest Excel report from `/api/bench/download` — no modal required.

#### 8. Daily Report — Download as .txt
The Daily Report modal now has a **⬇ Download .txt** button alongside **Copy Report**. It builds the same plain-text format used by Copy Report and triggers a browser download as `BenchAgent_DailyReport_YYYYMMDD.txt`.

#### 9. Meeting Agenda Modal
A **Meeting Agenda** button was added to the header. It opens `AgendaModal`, which fetches `/api/bench/meeting-agenda` and displays a structured pre-meeting briefing with key discussion points and recommended decisions.

---

### Updated Component List

| Component | Change |
|---|---|
| `api.py` | Background thread lifespan; `_get_grade_band()` helper; `grade_band` query param on `/api/bench/deployment-matches`; `ready=True` set only after all rule outputs computed |
| `App.tsx` | `/health` polling on offline; `useRef` interval cleanup |
| `api.ts` | `fetchDeploymentMatches(gradeBand?)` accepts optional grade band |
| `Header.tsx` | Added `onDownloadExcel` prop and Excel download button |
| `DigestModal.tsx` | Added `handleDownloadTxt()` and ⬇ Download .txt button |
| `SkillGap.tsx` | Complete rewrite — self-fetching, sticky filter bar, split view, bar chart, three-column card layout, grade band filter, skill search, pulse animation |
| `AgendaModal.tsx` | New — Meeting Agenda modal |
