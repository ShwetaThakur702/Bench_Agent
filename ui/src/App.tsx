import { useEffect, useState } from 'react'
import { fetchAll } from './api'
import Header from './components/Header'
import TabNav from './components/TabNav'
import BenchSummary from './components/BenchSummary'
import Forecast from './components/Forecast'
import ThresholdAlerts from './components/ThresholdAlerts'
import HiringFreeze from './components/HiringFreeze'
import { sampleSnapshot, sampleForecast, sampleAlerts, sampleFreeze } from './sampleData'
import { AlertRow, ForecastRow, FreezeRow, SnapshotData } from './types'

type Tab = 'summary' | 'forecast' | 'alerts' | 'freeze'

export default function App() {
  const [tab, setTab] = useState<Tab>('summary')
  const [offline, setOffline] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)

  const [snapshot, setSnapshot] = useState<SnapshotData>(sampleSnapshot)
  const [forecast, setForecast] = useState<ForecastRow[]>(sampleForecast)
  const [alerts, setAlerts]     = useState<AlertRow[]>(sampleAlerts)
  const [freeze, setFreeze]     = useState<FreezeRow[]>(sampleFreeze)

  useEffect(() => {
    fetchAll()
      .then(({ data }) => {
        setSnapshot(data.snapshot)
        setForecast(data.forecast)
        setAlerts(data.alerts)
        setFreeze(data.freeze)
        setOffline(false)
        setLastUpdated(new Date().toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }))
      })
      .catch(() => {
        setOffline(true)
        setLastUpdated(new Date().toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }))
      })
  }, [])

  return (
    <>
      <Header offline={offline} lastUpdated={lastUpdated} />
      <TabNav active={tab} onChange={(t) => setTab(t as Tab)} />
      <main className="app-main">
        {tab === 'summary'  && <BenchSummary data={snapshot} />}
        {tab === 'forecast' && <Forecast data={forecast} />}
        {tab === 'alerts'   && <ThresholdAlerts data={alerts} />}
        {tab === 'freeze'   && <HiringFreeze data={freeze} />}
      </main>
    </>
  )
}
