import axios from 'axios'
import { ActionItem, AlertRow, DeploymentMatchRow, DigestReport, ForecastRow, FreezeRow, MeetingAgenda, OrgSliceForecastRow, RmNudge, SnapshotData } from './types'

const BASE = ''  // relative: proxied via Vite in dev, same-origin in production

export interface ApiData {
  snapshot: SnapshotData
  forecast: ForecastRow[]
  alerts: AlertRow[]
  freeze: FreezeRow[]
}

export async function fetchAll(): Promise<{ data: ApiData; offline: boolean }> {
  const [snapshot, forecast, alerts, freeze] = await Promise.all([
    axios.get<SnapshotData>(`${BASE}/api/bench/snapshot`),
    axios.get<ForecastRow[]>(`${BASE}/api/bench/forecast`),
    axios.get<AlertRow[]>(`${BASE}/api/bench/alerts`),
    axios.get<FreezeRow[]>(`${BASE}/api/bench/hiring-freeze`),
  ])
  return {
    data: {
      snapshot: snapshot.data,
      forecast: forecast.data,
      alerts: alerts.data,
      freeze: freeze.data,
    },
    offline: false,
  }
}

export async function fetchActions(): Promise<ActionItem[]> {
  const res = await axios.get<ActionItem[]>(`${BASE}/api/bench/actions`)
  return res.data
}

export async function fetchDeploymentMatches(gradeBand = 'All'): Promise<DeploymentMatchRow[]> {
  const qs = gradeBand !== 'All' ? `?grade_band=${encodeURIComponent(gradeBand)}` : ''
  const res = await axios.get<DeploymentMatchRow[]>(`${BASE}/api/bench/deployment-matches${qs}`)
  return res.data
}

export async function fetchOrgSliceForecast(): Promise<OrgSliceForecastRow[]> {
  const res = await axios.get<OrgSliceForecastRow[]>(`${BASE}/api/bench/forecast/org-breakdown`)
  return res.data
}

export async function fetchDigest(): Promise<DigestReport> {
  const res = await axios.get<DigestReport>(`${BASE}/api/bench/digest`)
  return res.data
}

export async function fetchRmNudges(): Promise<RmNudge[]> {
  const res = await axios.get<RmNudge[]>(`${BASE}/api/bench/rm-nudges`)
  return res.data
}

export async function fetchAgenda(): Promise<MeetingAgenda> {
  const res = await axios.get<MeetingAgenda>(`${BASE}/api/bench/meeting-agenda`)
  return res.data
}
