export interface SnapshotData {
  total_headcount: number
  run_date: string
  status_counts: Record<string, number>
  current_vs_future: Record<string, number>
  aging_distribution: Record<string, number>
  by_location: Record<string, number>
}

export interface ForecastRow {
  forecast_date: string
  days_from_today: number
  total_forecast_bench: number
  confirmed_count: number
  projected_count: number
  forecast_confidence_band: string
  bucket: string
}

export type AlertSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'OK'

export interface AlertRow {
  org_slice: string
  current_bench_count: number
  bench_threshold: number
  breach_amount: number
  is_breached: boolean
  alert_severity: AlertSeverity
  recommended_action: string
  run_date: string
}

export interface FreezeRow {
  skill: string
  bench_count: number
  near_term_releases: number
  total_supply: number
  open_demand_count: number
  supply_surplus: number
  freeze_recommended: boolean
  avg_skill_rating: number | null
  advisory_note: string
  run_date: string
  llm_narrative?: string
}
