import {
  Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { ForecastRow } from '../types'

interface Props { data: ForecastRow[] }

export default function Forecast({ data }: Props) {
  const refDates = [30, 60, 90].map((day) => ({
    day,
    date: data.find((r) => r.days_from_today === day)?.forecast_date ?? '',
  }))

  const tickFormatter = (v: string) => {
    const d = new Date(v)
    return `${d.getMonth() + 1}/${d.getDate()}`
  }

  return (
    <section>
      <h2 className="section-title">30 / 60 / 90-Day Forecast</h2>
      <div className="card">
        <div className="card-label">Daily Bench Headcount — Confirmed vs Projected Releases</div>
        <div className="chart-box-tall">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 24, bottom: 8, left: 0 }}>
              <XAxis
                dataKey="forecast_date"
                tick={{ fontSize: 9 }}
                interval={14}
                tickFormatter={tickFormatter}
              />
              <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
              <Tooltip
                labelFormatter={(label: string) => `Date: ${label}`}
                formatter={(value: number, name: string) => [value, name]}
              />
              <Legend iconSize={12} wrapperStyle={{ fontSize: 11 }} />

              {refDates.map(({ day, date }) =>
                date ? (
                  <ReferenceLine
                    key={day}
                    x={date}
                    stroke="#94a3b8"
                    strokeDasharray="4 4"
                    label={{ value: `Day ${day}`, position: 'insideTopRight', fontSize: 9, fill: '#64748b' }}
                  />
                ) : null
              )}

              <Line
                type="monotone"
                dataKey="confirmed_count"
                name="Confirmed (HIGH confidence)"
                stroke="#3B1F6B"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="projected_count"
                name="Projected (MIXED confidence)"
                stroke="#C8E000"
                strokeWidth={2}
                strokeDasharray="7 4"
                dot={false}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  )
}
