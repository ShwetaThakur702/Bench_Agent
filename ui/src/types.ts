export interface SnapshotData {
  total_headcount: number
  at_risk_count: number
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

export interface OrgSliceForecastRow {
  org_slice: string
  bucket: '30d' | '60d' | '90d'
  count: number
}

export type CoverageLevel = 'FULL' | 'PARTIAL' | 'NONE'

export interface DeploymentMatchRow {
  skill: string
  open_demand_count: number
  matched_bench_count: number
  match_rate_pct: number
  coverage: CoverageLevel
  gap: number
  run_date: string
}

export interface ActionItem {
  rule: 'R1' | 'R2' | 'R3' | 'R4'
  priority: 'IMMEDIATE' | '7-DAY' | '30-DAY'
  owner: 'RM' | 'HR' | 'Leadership'
  action: string
  rationale: string
  org_slice?: string
  skill?: string
  hr_email?: { subject: string; body: string }
}

export interface DigestBenchHealth {
  total_bench: number
  current_bench: number
  future_bench: number
  at_risk_count: number
  status: 'HEALTHY' | 'WATCH' | 'CRITICAL'
}

export interface DigestReport {
  report_date: string
  report_title: string
  executive_summary: string
  bench_health: DigestBenchHealth
  top_actions: ActionItem[]
  threshold_breaches: AlertRow[]
  freeze_recommendations: FreezeRow[]
  releases_in_30_days: number
  generated_at: string
}

export interface RmNudge {
  rm_name: string
  employee_count: number
  email_subject: string
  email_body: string
  urgency: 'HIGH' | 'MEDIUM'
}

export interface MeetingAgendaSection {
  section: string
  duration_mins: number
  points: string[]
}

export interface MeetingAgenda {
  meeting_date: string
  meeting_date_human: string
  meeting_title: string
  prepared_by: string
  sections: MeetingAgendaSection[]
  total_duration_mins: number
  disclaimer: string
}
