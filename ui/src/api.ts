import axios from 'axios'
import { AlertRow, ForecastRow, FreezeRow, SnapshotData } from './types'

const BASE = 'http://localhost:8000'

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
