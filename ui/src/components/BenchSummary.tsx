import { useEffect, useRef, useState } from 'react'
import {
  Bar, BarChart, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { SnapshotData } from '../types'

interface Props { data: SnapshotData }

function useCountUp(target: number, duration = 1500) {
  const [count, setCount] = useState(0)
  const raf = useRef<number>(0)
  useEffect(() => {
    const start = performance.now()
    function tick(now: number) {
      const t = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setCount(Math.round(eased * target))
      if (t < 1) raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [target, duration])
  return count
}

const AGING_ORDER = ['<30 days', '31-60 days', '61-90 days', '>91 days', 'Unknown']
const AGING_COLOR: Record<string, string> = {
  '<30 days':   '#2D7A3A',
  '31-60 days': '#F59E0B',
  '61-90 days': '#F97316',
  '>91 days':   '#EF4444',
  'Unknown':    '#9CA3AF',
}

const CHART_COLORS = ['#4361EE', '#2D7A3A', '#F59E0B', '#EF4444', '#8B5CF6', '#0EA5E9']

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 12, padding: '10px 14px',
      boxShadow: 'var(--shadow-md)', fontSize: 12, minWidth: 130,
    }}>
      {label && <div style={{ fontWeight: 700, marginBottom: 6, color: 'var(--text)', fontSize: 12 }}>{label}</div>}
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 7, color: 'var(--text-3)', padding: '2px 0' }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: p.color || p.fill, display: 'inline-block', flexShrink: 0 }} />
          <span>{p.name}:</span>
          <strong style={{ color: 'var(--text)' }}>{p.value}</strong>
        </div>
      ))}
    </div>
  )
}

const IconTrendUp = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
    <polyline points="1,11 6,6 10,8 15,3" />
    <polyline points="10,3 15,3 15,8" />
  </svg>
)
const IconAlert = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
    <path d="M8 2L1.5 13.5h13L8 2z" />
    <line x1="8" y1="7" x2="8" y2="10" />
    <circle cx="8" cy="12.5" r=".6" fill="currentColor" stroke="none" />
  </svg>
)
const IconAlertCircle = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
    <circle cx="8" cy="8" r="6.5" />
    <line x1="8" y1="5" x2="8" y2="8.5" />
    <circle cx="8" cy="11" r=".6" fill="currentColor" stroke="none" />
  </svg>
)

export default function BenchSummary({ data }: Props) {
  const animatedCount = useCountUp(data.total_headcount)

  const agingData = AGING_ORDER
    .filter((k) => (data.aging_distribution[k] ?? 0) > 0 || k === '>91 days')
    .map((name) => ({ name, count: data.aging_distribution[name] ?? 0 }))

  const cvfData = Object.entries(data.current_vs_future).map(([name, value]) => ({ name, value }))
  const locData = Object.entries(data.by_location).map(([name, value]) => ({ name, value }))

  const fresh    = data.aging_distribution['<30 days'] ?? 0
  const critical = data.aging_distribution['>91 days'] ?? 0
  const atRisk   = data.aging_distribution['61-90 days'] ?? 0

  return (
    <section>
      <h2 className="section-title">
        <span className="section-title-icon">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="1" y="1" width="6" height="6" rx="1" /><rect x="9" y="1" width="6" height="6" rx="1" />
            <rect x="1" y="9" width="6" height="6" rx="1" /><rect x="9" y="9" width="6" height="6" rx="1" />
          </svg>
        </span>
        Bench Summary
      </h2>

      <div className="stat-cards-row" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
        <div className="stat-card stat-card-1">
          <div className="stat-card-label">Total Headcount</div>
          <div className="stat-card-val">{animatedCount}</div>
          <div className="stat-card-sub">Deployable bench</div>
        </div>
        <div className="stat-card stat-card-2">
          <div className="stat-card-label">Fresh Talent</div>
          <div className="stat-card-val">{fresh}</div>
          <div className="stat-card-sub">Under 30 days on bench</div>
        </div>
        <div className="stat-card stat-card-3">
          <div className="stat-card-label">Aging Risk</div>
          <div className="stat-card-val">{atRisk}</div>
          <div className="stat-card-sub">61–90 days on bench</div>
        </div>
        <div className="stat-card stat-card-4">
          <div className="stat-card-label">Critical Aging</div>
          <div className="stat-card-val">{critical}</div>
          <div className="stat-card-sub">Over 91 days on bench</div>
        </div>
        <div className="stat-card" style={{ background: 'linear-gradient(135deg, #EF4444 0%, #F87171 100%)' }}>
          <div className="stat-card-label">⚠ At Risk</div>
          <div className="stat-card-val">{data.at_risk_count}</div>
          <div className="stat-card-sub">Aging &gt;60d · not proposed</div>
        </div>
      </div>

      <div className="summary-charts-row">
        <div className="card">
          <div className="card-label">Current vs Future Bench</div>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={cvfData} dataKey="value" innerRadius="50%" outerRadius="76%" paddingAngle={3} strokeWidth={0}>
                  {cvfData.map((_e, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: 'var(--text-3)' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-label">Location Split</div>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={locData} dataKey="value" innerRadius="50%" outerRadius="76%" paddingAngle={3} strokeWidth={0}>
                  {locData.map((_e, i) => <Cell key={i} fill={CHART_COLORS[(i + 2) % CHART_COLORS.length]} />)}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: 'var(--text-3)' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="kpi-strip">
          <div className="kpi-card kpi-card-green">
            <div className="kpi-icon"><IconTrendUp /></div>
            <div className="kpi-data">
              <div className="kpi-value">{fresh}</div>
              <div className="kpi-label">Fresh — under 30 days</div>
            </div>
          </div>
          <div className="kpi-card kpi-card-yellow">
            <div className="kpi-icon"><IconAlert /></div>
            <div className="kpi-data">
              <div className="kpi-value">{atRisk}</div>
              <div className="kpi-label">At Risk — 61–90 days</div>
            </div>
          </div>
          <div className="kpi-card kpi-card-red">
            <div className="kpi-icon"><IconAlertCircle /></div>
            <div className="kpi-data">
              <div className="kpi-value">{critical}</div>
              <div className="kpi-label">Critical — over 91 days</div>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-label">Bench Aging Distribution</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          {agingData.map((entry) => (
            <div key={entry.name} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '5px 12px', borderRadius: 999,
              background: 'var(--surface-2)', border: '1.5px solid var(--border-2)',
              fontSize: 12, fontWeight: 600, color: 'var(--text-2)',
            }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: AGING_COLOR[entry.name] ?? '#9CA3AF', display: 'inline-block', flexShrink: 0 }} />
              {entry.name}
              <span style={{ background: AGING_COLOR[entry.name] ?? '#9CA3AF', color: '#fff', borderRadius: 999, padding: '1px 7px', fontSize: 11, fontWeight: 700 }}>
                {entry.count}
              </span>
            </div>
          ))}
        </div>
        <div style={{ height: 44 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart layout="vertical" data={agingData} margin={{ left: 0, right: 20, top: 0, bottom: 0 }}>
              <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-4)' }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={false} width={0} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={16} animationDuration={800}>
                {agingData.map((entry) => <Cell key={entry.name} fill={AGING_COLOR[entry.name] ?? '#9CA3AF'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  )
}
