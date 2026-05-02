import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { fetchAll, fetchActions, fetchDeploymentMatches, fetchOrgSliceForecast, fetchRmNudges } from './api'
import Header from './components/Header'
import TabNav from './components/TabNav'
import BenchSummary from './components/BenchSummary'
import Forecast from './components/Forecast'
import ThresholdAlerts from './components/ThresholdAlerts'
import HiringFreeze from './components/HiringFreeze'
import ActionCards from './components/ActionCards'
import DeploymentMatches from './components/DeploymentMatches'
import SkillGap from './components/SkillGap'
import DigestModal from './components/DigestModal'
import AgendaModal from './components/AgendaModal'
import Skeleton from './components/Skeleton'
import {
  sampleSnapshot, sampleForecast, sampleAlerts,
  sampleFreeze, sampleActions, sampleDeploymentMatches,
  sampleOrgSliceForecast, sampleRmNudges,
} from './sampleData'
import {
  ActionItem, AlertRow, DeploymentMatchRow,
  ForecastRow, FreezeRow, OrgSliceForecastRow, RmNudge, SnapshotData,
} from './types'

type Tab = 'summary' | 'actions' | 'forecast' | 'alerts' | 'freeze' | 'matches' | 'skillgap'

export default function App() {
  const [tab, setTab]           = useState<Tab>('summary')
  const [offline, setOffline]   = useState(false)
  const [isLoading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)
  const [dark, setDark]         = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [snapshot, setSnapshot]   = useState<SnapshotData>(sampleSnapshot)
  const [forecast, setForecast]   = useState<ForecastRow[]>(sampleForecast)
  const [alerts, setAlerts]       = useState<AlertRow[]>(sampleAlerts)
  const [freeze, setFreeze]       = useState<FreezeRow[]>(sampleFreeze)
  const [actions, setActions]     = useState<ActionItem[]>(sampleActions)
  const [matches, setMatches]     = useState<DeploymentMatchRow[]>(sampleDeploymentMatches)
  const [orgBreak, setOrgBreak]   = useState<OrgSliceForecastRow[]>(sampleOrgSliceForecast)
  const [rmNudges, setRmNudges]   = useState<RmNudge[]>([])
  const [showDigest, setShowDigest] = useState(false)
  const [showAgenda, setShowAgenda] = useState(false)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
  }, [dark])

  function loadLiveData() {
    const ts = new Date().toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
    return fetchAll()
      .then(({ data }) => {
        setSnapshot(data.snapshot)
        setForecast(data.forecast)
        setAlerts(data.alerts)
        setFreeze(data.freeze)
        setOffline(false)
        setLastUpdated(ts)
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
        return Promise.all([
          fetchActions().catch(() => sampleActions),
          fetchDeploymentMatches().catch(() => sampleDeploymentMatches),
          fetchOrgSliceForecast().catch(() => sampleOrgSliceForecast),
          fetchRmNudges().catch(() => sampleRmNudges),
        ])
      })
      .then(([acts, mtch, org, nudges]) => {
        setActions(acts)
        setMatches(mtch)
        setOrgBreak(org)
        setRmNudges(nudges)
      })
  }

  useEffect(() => {
    const ts = new Date().toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
    loadLiveData()
      .catch(() => {
        setOffline(true)
        setLastUpdated(ts)
        // Poll /health every 5s — re-fetch data once backend pipeline is ready
        pollRef.current = setInterval(() => {
          axios.get('/health')
            .then(({ data }) => {
              if (data.pipeline_ready) loadLiveData().finally(() => setLoading(false))
            })
            .catch(() => {})
        }, 5000)
      })
      .finally(() => setLoading(false))
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      {showDigest && <DigestModal onClose={() => setShowDigest(false)} />}
      {showAgenda && <AgendaModal onClose={() => setShowAgenda(false)} />}
      <Header
        offline={offline}
        lastUpdated={lastUpdated}
        dark={dark}
        onToggleDark={() => setDark((d) => !d)}
        onOpenDailyReport={() => setShowDigest(true)}
        onOpenAgenda={() => setShowAgenda(true)}
        onDownloadExcel={() => {
          const a = document.createElement('a')
          a.href = '/api/bench/download'
          a.click()
        }}
      />
      <TabNav active={tab} onChange={(t) => setTab(t as Tab)} />
      <main className="app-main">
        {isLoading ? (
          <Skeleton />
        ) : (
          <>
            {tab === 'summary'  && <BenchSummary data={snapshot} />}
            {tab === 'actions'  && <ActionCards data={actions} rmNudges={rmNudges} />}
            {tab === 'forecast' && <Forecast data={forecast} orgBreakdown={orgBreak} />}
            {tab === 'alerts'   && <ThresholdAlerts data={alerts} actions={actions} />}
            {tab === 'freeze'   && <HiringFreeze data={freeze} actions={actions} />}
            {tab === 'matches'  && <DeploymentMatches data={matches} />}
            {tab === 'skillgap' && <SkillGap />}
          </>
        )}
      </main>
    </>
  )
}
