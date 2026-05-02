import { ActionItem, AlertRow, DeploymentMatchRow, ForecastRow, FreezeRow, OrgSliceForecastRow, RmNudge, SnapshotData } from './types'

const TODAY = new Date().toISOString().slice(0, 10)

function addDays(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

export const sampleSnapshot: SnapshotData = {
  total_headcount: 80,
  at_risk_count: 39,
  run_date: TODAY,
  status_counts: { available: 6, proposed: 19, allocated: 4, nafd: 29, other: 22 },
  current_vs_future: { 'Current bench': 39, 'Future bench': 41 },
  aging_distribution: { '>91 days': 39, 'Unknown': 41 },
  by_location: { Onsite: 63, Offshore: 17 },
}

export const sampleForecast: ForecastRow[] = Array.from({ length: 91 }, (_, i) => ({
  forecast_date: addDays(i),
  days_from_today: i,
  total_forecast_bench: i >= 88 ? 1 : 0,
  confirmed_count: i >= 88 ? 1 : 0,
  projected_count: 0,
  forecast_confidence_band: 'HIGH',
  bucket: i <= 30 ? '30d' : i <= 60 ? '60d' : '90d',
}))

export const sampleAlerts: AlertRow[] = [
  { org_slice: 'CYBER_SEC',      current_bench_count: 6, bench_threshold: 3,  breach_amount:  3, is_breached: true,  alert_severity: 'MEDIUM', recommended_action: 'Review bench pipeline for CYBER_SEC. Current bench (6) exceeds threshold (3) by 3.', run_date: TODAY },
  { org_slice: 'DIGITAL_ENG',    current_bench_count: 4, bench_threshold: 5,  breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
  { org_slice: 'CLOUD_INFRA',    current_bench_count: 3, bench_threshold: 4,  breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
  { org_slice: 'DATA_ANALYTICS', current_bench_count: 5, bench_threshold: 6,  breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
  { org_slice: 'JAVA_PRACTICE',  current_bench_count: 7, bench_threshold: 8,  breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
  { org_slice: 'QA_AUTOMATION',  current_bench_count: 3, bench_threshold: 4,  breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
  { org_slice: 'SAP_PRACTICE',   current_bench_count: 9, bench_threshold: 10, breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
  { org_slice: 'DEVOPS_SRE',     current_bench_count: 2, bench_threshold: 3,  breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
  { org_slice: 'AI_ML',          current_bench_count: 4, bench_threshold: 5,  breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
  { org_slice: 'FULLSTACK_WEB',  current_bench_count: 6, bench_threshold: 7,  breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
  { org_slice: 'ERP_FUNCTIONAL', current_bench_count: 3, bench_threshold: 4,  breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
  { org_slice: 'TESTING_PERF',   current_bench_count: 2, bench_threshold: 3,  breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
  { org_slice: 'MOBILE_DEV',     current_bench_count: 2, bench_threshold: 3,  breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
  { org_slice: 'ARCHITECTURE',   current_bench_count: 1, bench_threshold: 2,  breach_amount: -1, is_breached: false, alert_severity: 'OK',     recommended_action: 'No action required.', run_date: TODAY },
]

export const sampleFreeze: FreezeRow[] = [
  { skill: 'ERP-SAP',     bench_count: 7, near_term_releases: 0, total_supply: 7, open_demand_count: 2, supply_surplus:  5, freeze_recommended: true,  avg_skill_rating: 1.5, advisory_note: 'Supply (7) exceeds demand (2) by 5.', run_date: TODAY, llm_narrative: 'Implement an immediate hiring freeze for ERP-SAP. Surplus 5, avg rating 1.5. Review: 30-day.' },
  { skill: 'Selenium',    bench_count: 5, near_term_releases: 0, total_supply: 5, open_demand_count: 2, supply_surplus:  3, freeze_recommended: true,  avg_skill_rating: 3.5, advisory_note: 'Supply (5) exceeds demand (2) by 3.', run_date: TODAY, llm_narrative: 'Apply targeted hiring freeze for Selenium. Surplus 3. Review: 30-day.' },
  { skill: 'Spring Boot', bench_count: 5, near_term_releases: 0, total_supply: 5, open_demand_count: 3, supply_surplus:  2, freeze_recommended: true,  avg_skill_rating: 3.0, advisory_note: 'Supply (5) exceeds demand (3) by 2.', run_date: TODAY, llm_narrative: 'Enact hiring freeze for Spring Boot. Surplus 2. Review: 60-day.' },
  { skill: 'Docker',      bench_count: 4, near_term_releases: 0, total_supply: 4, open_demand_count: 3, supply_surplus:  1, freeze_recommended: true,  avg_skill_rating: 3.0, advisory_note: 'Supply (4) exceeds demand (3) by 1.', run_date: TODAY, llm_narrative: 'Initiate hiring freeze for Docker. Surplus 1. Review: 60-day.' },
  { skill: 'AWS',         bench_count: 4, near_term_releases: 0, total_supply: 4, open_demand_count: 3, supply_surplus:  1, freeze_recommended: true,  avg_skill_rating: 2.0, advisory_note: 'Supply (4) exceeds demand (3) by 1.', run_date: TODAY, llm_narrative: 'Freeze AWS hiring. Surplus 1. Review: 60-day.' },
  { skill: 'Java',        bench_count: 2, near_term_releases: 0, total_supply: 2, open_demand_count: 8, supply_surplus: -6, freeze_recommended: false, avg_skill_rating: null, advisory_note: 'Demand (8) exceeds supply (2) by 6. No freeze needed.', run_date: TODAY },
  { skill: 'Python',      bench_count: 3, near_term_releases: 0, total_supply: 3, open_demand_count: 9, supply_surplus: -6, freeze_recommended: false, avg_skill_rating: null, advisory_note: 'Demand (9) exceeds supply (3) by 6. No freeze needed.', run_date: TODAY },
  { skill: 'React',       bench_count: 1, near_term_releases: 0, total_supply: 1, open_demand_count: 6, supply_surplus: -5, freeze_recommended: false, avg_skill_rating: null, advisory_note: 'Demand (6) exceeds supply (1) by 5. No freeze needed.', run_date: TODAY },
  { skill: 'Kubernetes',  bench_count: 0, near_term_releases: 0, total_supply: 0, open_demand_count: 3, supply_surplus: -3, freeze_recommended: false, avg_skill_rating: null, advisory_note: 'Demand (3) exceeds supply (0) by 3. No freeze needed.', run_date: TODAY },
  { skill: 'Terraform',   bench_count: 1, near_term_releases: 0, total_supply: 1, open_demand_count: 3, supply_surplus: -2, freeze_recommended: false, avg_skill_rating: null, advisory_note: 'Demand (3) exceeds supply (1) by 2. No freeze needed.', run_date: TODAY },
]

export const sampleActions: ActionItem[] = [
  { rule: 'R1', priority: 'IMMEDIATE', owner: 'RM',
    action: 'Schedule placement review for 6 "Available for mapping" employees. 39 have exceeded 91 days on bench.',
    rationale: '6 deployable employees have no proposed opportunity. 39 crossed the 91-day aging threshold.' },
  { rule: 'R1', priority: '7-DAY', owner: 'Leadership',
    action: 'Convene bench review meeting — 29 of 80 bench employees (36%) carry NAFD status.',
    rationale: 'NAFD count exceeds 20% of total deployable bench. Leadership review needed.' },
  { rule: 'R2', priority: 'IMMEDIATE', owner: 'RM',
    action: 'Begin pre-mapping for 10 resources forecasted to join bench within 30 days.',
    rationale: '30-day forecast shows 10 additional resources entering bench — a 13% increase.' },
  { rule: 'R2', priority: '7-DAY', owner: 'RM',
    action: 'Confirm release dates with project managers for all projected bench additions.',
    rationale: 'Majority of forecast days show MIXED confidence. Inaccurate forecasts cause last-minute bench spikes.' },
  { rule: 'R3', priority: 'IMMEDIATE', owner: 'HR', org_slice: 'CYBER_SEC',
    action: 'Pause all active hiring requisitions for CYBER_SEC immediately.',
    rationale: 'CYBER_SEC bench (6) exceeds configured threshold (3) by 3. Continuing to hire deepens bench cost.' },
  { rule: 'R3', priority: '7-DAY', owner: 'RM', org_slice: 'CYBER_SEC',
    action: 'Review all 6 CYBER_SEC bench employees for redeployment — identify skill adjacencies.',
    rationale: 'Threshold breach of 3 in CYBER_SEC means more bench than planned capacity.' },
  { rule: 'R3', priority: '30-DAY', owner: 'Leadership', org_slice: 'CYBER_SEC',
    action: 'If CYBER_SEC bench remains undeployed at 30-day mark, initiate skill transition / reskilling plan.',
    rationale: 'Persistent threshold breach beyond 30 days signals a structural mismatch.' },
  { rule: 'R4', priority: 'IMMEDIATE', owner: 'HR', skill: 'ERP-SAP',
    action: "Implement hiring freeze for 'ERP-SAP' skill cluster. Notify recruiters and pause open requisitions.",
    rationale: "Bench supply (7) exceeds open demand (2) by 5 for 'ERP-SAP'.",
    hr_email: {
      subject: 'Hiring Freeze Recommendation — ERP-SAP Skill Cluster',
      body: 'Dear HR Team,\n\nFollowing a review of our current bench supply and open demand pipeline, we recommend implementing a hiring freeze for the ERP-SAP skill cluster immediately.\n\nCurrent bench supply stands at 7 resources against 2 open demand positions, resulting in a surplus of 5. The average skill rating across the bench pool is 1.5. Continuing to recruit for this cluster would further widen the surplus and increase bench carrying costs with no clear deployment path.\n\nWe recommend pausing all active ERP-SAP requisitions for a 30-day review period. During this window, the RM team will work to map existing bench resources to open demands before any new recruitment is approved. Please confirm receipt and update all active requisition statuses to "On Hold" accordingly.\n\nRegards,\nBench Agent (Advisory System — for review before sending)',
    },
  },
  { rule: 'R4', priority: '7-DAY', owner: 'HR', skill: 'Selenium',
    action: "Implement hiring freeze for 'Selenium' skill cluster.",
    rationale: "Bench supply (5) exceeds open demand (2) by 3 for 'Selenium'.",
    hr_email: {
      subject: 'Hiring Freeze Recommendation — Selenium Skill Cluster',
      body: 'Dear HR Team,\n\nFollowing a review, we recommend implementing a hiring freeze for the Selenium skill cluster within the next 30 days.\n\nCurrent bench supply stands at 5 resources against 2 open demand positions, resulting in a surplus of 3. The average skill rating is 3.5.\n\nWe recommend pausing all active Selenium requisitions for a 30-day review period. Please confirm receipt and update requisition statuses to "On Hold".\n\nRegards,\nBench Agent (Advisory System — for review before sending)',
    },
  },
  { rule: 'R4', priority: '7-DAY', owner: 'HR', skill: 'Spring Boot',
    action: "Implement hiring freeze for 'Spring Boot' skill cluster.",
    rationale: "Bench supply (5) exceeds open demand (3) by 2 for 'Spring Boot'.",
    hr_email: {
      subject: 'Hiring Freeze Recommendation — Spring Boot Skill Cluster',
      body: 'Dear HR Team,\n\nWe recommend implementing a hiring freeze for the Spring Boot skill cluster within the next 30 days.\n\nCurrent bench supply: 5 resources. Open demand: 3 positions. Surplus: 2. Average skill rating: 3.0.\n\nPlease pause all active Spring Boot requisitions for a 30-day review period.\n\nRegards,\nBench Agent (Advisory System — for review before sending)',
    },
  },
]

export const sampleDeploymentMatches: DeploymentMatchRow[] = [
  { skill: 'Kubernetes',  open_demand_count: 3, matched_bench_count: 0, match_rate_pct: 0,    coverage: 'NONE',    gap: 3,  run_date: TODAY },
  { skill: 'Terraform',   open_demand_count: 3, matched_bench_count: 0, match_rate_pct: 0,    coverage: 'NONE',    gap: 3,  run_date: TODAY },
  { skill: 'React',       open_demand_count: 6, matched_bench_count: 1, match_rate_pct: 16.7, coverage: 'PARTIAL', gap: 5,  run_date: TODAY },
  { skill: 'Python',      open_demand_count: 9, matched_bench_count: 3, match_rate_pct: 33.3, coverage: 'PARTIAL', gap: 6,  run_date: TODAY },
  { skill: 'Java',        open_demand_count: 8, matched_bench_count: 2, match_rate_pct: 25.0, coverage: 'PARTIAL', gap: 6,  run_date: TODAY },
  { skill: 'ERP-SAP',     open_demand_count: 2, matched_bench_count: 7, match_rate_pct: 100,  coverage: 'FULL',    gap: -5, run_date: TODAY },
  { skill: 'Selenium',    open_demand_count: 2, matched_bench_count: 5, match_rate_pct: 100,  coverage: 'FULL',    gap: -3, run_date: TODAY },
  { skill: 'Spring Boot', open_demand_count: 3, matched_bench_count: 5, match_rate_pct: 100,  coverage: 'FULL',    gap: -2, run_date: TODAY },
  { skill: 'Docker',      open_demand_count: 3, matched_bench_count: 4, match_rate_pct: 100,  coverage: 'FULL',    gap: -1, run_date: TODAY },
  { skill: 'AWS',         open_demand_count: 3, matched_bench_count: 4, match_rate_pct: 100,  coverage: 'FULL',    gap: -1, run_date: TODAY },
]

export const sampleOrgSliceForecast: OrgSliceForecastRow[] = [
  { org_slice: 'CYBER_SEC',      bucket: '30d', count: 3 },
  { org_slice: 'DATA_ANALYTICS', bucket: '30d', count: 2 },
  { org_slice: 'JAVA_PRACTICE',  bucket: '30d', count: 4 },
  { org_slice: 'CLOUD_INFRA',    bucket: '60d', count: 2 },
  { org_slice: 'CYBER_SEC',      bucket: '60d', count: 1 },
  { org_slice: 'DEVOPS_SRE',     bucket: '60d', count: 3 },
  { org_slice: 'AI_ML',          bucket: '90d', count: 2 },
  { org_slice: 'FULLSTACK_WEB',  bucket: '90d', count: 1 },
  { org_slice: 'JAVA_PRACTICE',  bucket: '90d', count: 2 },
  { org_slice: 'QA_AUTOMATION',  bucket: '90d', count: 1 },
]

export const sampleRmNudges: RmNudge[] = [
  {
    rm_name: 'RM Name A',
    employee_count: 4,
    email_subject: 'Action Required — Bench Status Update Needed',
    email_body: 'Hi RM Name A,\n\nThe following 4 employees under your account have been on bench\nfor over 60 days without a proposed or shortlisted status.\nPlease update their deployment status in RIS by end of day.\n\nEmployees requiring status update:\n- 2 employees in Java with avg bench aging 95 days\n- 2 employees in Python with avg bench aging 75 days\n\nCurrent bench aging thresholds:\n- >60 days without proposed status = escalation required\n- >90 days = leadership review triggered\n\nPlease log into RIS and update the Final Status field for these resources.\n\nThis is an automated advisory from Bench Agent.\n[Advisory only — Bench Agent cannot modify RIS]',
    urgency: 'HIGH',
  },
  {
    rm_name: 'RM Name B',
    employee_count: 2,
    email_subject: 'Action Required — Bench Status Update Needed',
    email_body: 'Hi RM Name B,\n\nThe following 2 employees under your account have been on bench\nfor over 60 days without a proposed or shortlisted status.\nPlease update their deployment status in RIS by end of day.\n\nEmployees requiring status update:\n- 2 employees in ERP-SAP with avg bench aging 68 days\n\nCurrent bench aging thresholds:\n- >60 days without proposed status = escalation required\n- >90 days = leadership review triggered\n\nPlease log into RIS and update the Final Status field for these resources.\n\nThis is an automated advisory from Bench Agent.\n[ — Bench Agent cannot modify RIS]',
    urgency: 'MEDIUM',
  },
]
