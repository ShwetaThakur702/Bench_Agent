-- Bench Agent — PostgreSQL schema (Phase 6)
-- Apply with: psql -d bench_agent -f schema.sql

-- One row per pipeline run — full R1 KPI payload stored as JSONB
CREATE TABLE IF NOT EXISTS bench_snapshots (
    id              SERIAL PRIMARY KEY,
    run_date        DATE         NOT NULL,
    total_headcount INTEGER      NOT NULL,
    snapshot_json   JSONB        NOT NULL,
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

-- One row per calendar day per pipeline run (91 rows per run)
CREATE TABLE IF NOT EXISTS bench_forecasts (
    id                       SERIAL PRIMARY KEY,
    run_date                 DATE     NOT NULL,
    forecast_date            DATE     NOT NULL,
    days_from_today          INTEGER  NOT NULL,
    total_forecast_bench     INTEGER  NOT NULL,
    confirmed_count          INTEGER  NOT NULL,
    projected_count          INTEGER  NOT NULL,
    forecast_confidence_band TEXT     NOT NULL,
    bucket                   TEXT     NOT NULL,
    created_at               TIMESTAMPTZ DEFAULT NOW()
);

-- Unified alert table: both R3 threshold alerts and R4 hiring-freeze rows
-- alert_type: 'threshold' (R3) | 'freeze' (R4)
CREATE TABLE IF NOT EXISTS bench_alerts (
    id                  SERIAL PRIMARY KEY,
    run_date            DATE     NOT NULL,
    alert_type          TEXT     NOT NULL,
    org_slice_or_skill  TEXT     NOT NULL,
    current_count       INTEGER,
    threshold_or_demand INTEGER,
    breach_or_surplus   NUMERIC,
    alert_severity      TEXT,
    recommended_action  TEXT,
    llm_narrative       TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
