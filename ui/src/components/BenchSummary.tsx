import {
  Bar, BarChart, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { SnapshotData } from '../types'

interface Props { data: SnapshotData }

const AGING_ORDER = ['<30 days', '31-60 days', '61-90 days', '>91 days', 'Unknown']
const AGING_COLOR: Record<string, string> = {
  '<30 days':   '#22c55e',
  '31-60 days': '#eab308',
  '61-90 days': '#f97316',
  '>91 days':   '#ef4444',
  'Unknown':    '#94a3b8',
}

export default function BenchSummary({ data }: Props) {
  const agingData = AGING_ORDER
    .filter((k) => (data.aging_distribution[k] ?? 0) > 0 || k === '>91 days' || k === 'Unknown')
    .map((name) => ({ name, count: data.aging_distribution[name] ?? 0 }))

  const cvfData = Object.entries(data.current_vs_future).map(([name, value]) => ({ name, value }))
  const locData = Object.entries(data.by_location).map(([name, value]) => ({ name, value }))

  const DONUT_COLORS = ['#3B1F6B', '#C8E000']

  return (
    <section>
      <h2 className="section-title">Bench Summary</h2>
      <div className="summary-grid">

        {/* Headcount */}
        <div className="card headcount-card">
          <div className="headcount-num">{data.total_headcount}</div>
          <div className="headcount-lbl">Deployable Bench</div>
        </div>

        {/* Aging horizontal bar */}
        <div className="card">
          <div className="card-label">Bench Aging Distribution</div>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={agingData} margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={72} />
                <Tooltip formatter={(v: number) => [`${v} employees`, 'Count']} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={16}>
                  {agingData.map((entry) => (
                    <Cell key={entry.name} fill={AGING_COLOR[entry.name] ?? '#94a3b8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Current vs Future donut */}
        <div className="card">
          <div className="card-label">Current vs Future Bench</div>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={cvfData} dataKey="value" innerRadius="50%" outerRadius="75%" paddingAngle={3}>
                  {cvfData.map((_e, i) => (
                    <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number, name: string) => [v, name]} />
                <Legend iconType="circle" iconSize={10} wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Location donut */}
        <div className="card">
          <div className="card-label">Location Split</div>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={locData} dataKey="value" innerRadius="50%" outerRadius="75%" paddingAngle={3}>
                  {locData.map((_e, i) => (
                    <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number, name: string) => [v, name]} />
                <Legend iconType="circle" iconSize={10} wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </section>
  )
}
