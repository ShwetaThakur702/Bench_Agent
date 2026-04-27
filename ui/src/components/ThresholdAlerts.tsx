import { AlertRow, AlertSeverity } from '../types'

interface Props { data: AlertRow[] }

const ROW_CLASS: Record<AlertSeverity, string> = {
  CRITICAL: 'r-critical',
  HIGH:     'r-high',
  MEDIUM:   'r-medium',
  OK:       'r-ok',
}

const BADGE_CLASS: Record<AlertSeverity, string> = {
  CRITICAL: 'b-critical',
  HIGH:     'b-high',
  MEDIUM:   'b-medium',
  OK:       'b-ok',
}

export default function ThresholdAlerts({ data }: Props) {
  const breachedCount = data.filter((r) => r.is_breached).length

  return (
    <section>
      <h2 className="section-title">
        Threshold Alerts
        <span className="section-count">
          {data.length} org slices · {breachedCount} breached
        </span>
      </h2>
      <div className="card">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Org Slice</th>
                <th className="num">Current Bench</th>
                <th className="num">Threshold</th>
                <th className="num">Breach Amount</th>
                <th>Severity</th>
                <th>Recommended Action</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.org_slice} className={ROW_CLASS[row.alert_severity]}>
                  <td><strong>{row.org_slice}</strong></td>
                  <td className="num">{row.current_bench_count}</td>
                  <td className="num">{row.bench_threshold}</td>
                  <td className="num">
                    {row.breach_amount > 0
                      ? <span className="surplus-pos">+{row.breach_amount}</span>
                      : <span className="surplus-neg">{row.breach_amount}</span>}
                  </td>
                  <td>
                    <span className={`badge ${BADGE_CLASS[row.alert_severity]}`}>
                      {row.alert_severity}
                    </span>
                  </td>
                  <td style={{ maxWidth: 320, fontSize: 12 }}>{row.recommended_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
