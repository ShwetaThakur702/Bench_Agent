import { useState } from 'react'
import { ActionItem, AlertRow, AlertSeverity } from '../types'

interface Props {
  data: AlertRow[]
  actions?: ActionItem[]
}

const ROW_CLASS: Record<AlertSeverity, string> = {
  CRITICAL: 'r-critical', HIGH: 'r-high', MEDIUM: 'r-medium', OK: 'r-ok',
}
const BADGE_CLASS: Record<AlertSeverity, string> = {
  CRITICAL: 'b-critical', HIGH: 'b-high', MEDIUM: 'b-medium', OK: 'b-ok',
}
const SEV_PILL_CLASS: Record<AlertSeverity, string> = {
  CRITICAL: 'sev-critical', HIGH: 'sev-high', MEDIUM: 'sev-medium', OK: 'sev-ok',
}
const DOT_CLASS: Record<AlertSeverity, string> = {
  CRITICAL: 'sev-dot sev-dot-critical',
  HIGH:     'sev-dot sev-dot-high',
  MEDIUM:   'sev-dot sev-dot-medium',
  OK:       'sev-dot sev-dot-ok',
}
const SEV_LABEL: Record<AlertSeverity, string> = {
  CRITICAL: 'Critical', HIGH: 'High', MEDIUM: 'Medium', OK: 'OK',
}
const SEV_ORDER: AlertSeverity[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'OK']
const SEV_RANK: Record<AlertSeverity, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, OK: 3 }

const PRIORITY_CSS: Record<string, string> = {
  'IMMEDIATE': 'IMMEDIATE', '7-DAY': 'DAY7', '30-DAY': 'DAY30',
}

export default function ThresholdAlerts({ data: rawData, actions = [] }: Props) {
  const data = [...rawData].sort((a, b) => {
    const r = SEV_RANK[a.alert_severity] - SEV_RANK[b.alert_severity]
    return r !== 0 ? r : a.org_slice.localeCompare(b.org_slice)
  })
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const breachedCount = data.filter((r) => r.is_breached).length

  const sevCounts = SEV_ORDER.reduce((acc, s) => {
    acc[s] = data.filter((r) => r.alert_severity === s).length
    return acc
  }, {} as Record<AlertSeverity, number>)

  const actionsByOrg: Record<string, ActionItem[]> = {}
  for (const a of actions) {
    if (a.rule === 'R3' && a.org_slice) {
      if (!actionsByOrg[a.org_slice]) actionsByOrg[a.org_slice] = []
      actionsByOrg[a.org_slice].push(a)
    }
  }

  function toggle(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  return (
    <section>
      <h2 className="section-title">
        <span className="section-title-icon">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 2L1.5 13.5h13L8 2z" />
            <line x1="8" y1="7" x2="8" y2="10" />
            <circle cx="8" cy="12.5" r=".6" fill="currentColor" stroke="none" />
          </svg>
        </span>
        Threshold Alerts
        <span className="section-count">{data.length} org slices · {breachedCount} breached</span>
      </h2>

      <div className="severity-bar">
        {SEV_ORDER.filter((s) => sevCounts[s] > 0).map((s) => (
          <div key={s} className={`severity-pill ${SEV_PILL_CLASS[s]}`}>
            <span className={DOT_CLASS[s]} />
            {SEV_LABEL[s]}
            <span className="pill-count">{sevCounts[s]}</span>
          </div>
        ))}
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-scroll" style={{ border: 'none', borderRadius: 0 }}>
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
              {data.map((row) => {
                const hasActions = (actionsByOrg[row.org_slice]?.length ?? 0) > 0
                const isOpen = expanded.has(row.org_slice)
                return (
                  <>
                    <tr
                      key={row.org_slice}
                      className={`${ROW_CLASS[row.alert_severity]}${hasActions ? ' expand-trigger' : ''}`}
                      onClick={hasActions ? () => toggle(row.org_slice) : undefined}
                    >
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span className={DOT_CLASS[row.alert_severity]} />
                          <strong style={{ color: 'var(--text)', fontSize: 13 }}>{row.org_slice}</strong>
                          {hasActions && (
                            <span className={`expand-chevron${isOpen ? ' open' : ''}`}>▶</span>
                          )}
                        </div>
                      </td>
                      <td className="num"><span className="num-chip">{row.current_bench_count}</span></td>
                      <td className="num" style={{ color: 'var(--text-3)' }}>{row.bench_threshold}</td>
                      <td className="num">
                        {row.breach_amount > 0
                          ? <span className="surplus-pos">+{row.breach_amount}</span>
                          : <span className="surplus-neg">{row.breach_amount}</span>}
                      </td>
                      <td>
                        <span className={`badge ${BADGE_CLASS[row.alert_severity]}`}>{SEV_LABEL[row.alert_severity]}</span>
                      </td>
                      <td className="narrative">{row.recommended_action}</td>
                    </tr>
                    {hasActions && (
                      <tr key={`${row.org_slice}-expand`} className="expand-row">
                        <td colSpan={6}>
                          <div className={`expand-detail${isOpen ? ' open' : ''}`}>
                            <div className="expand-detail-inner">
                              <div className="expand-actions-list">
                                {actionsByOrg[row.org_slice].map((a, i) => {
                                  const css = PRIORITY_CSS[a.priority]
                                  return (
                                    <div key={i} className="expand-action-item">
                                      <div className="expand-action-meta">
                                        <span className="rule-tag">{a.rule}</span>
                                        <span className={`priority-pill ${css}`}>{a.priority}</span>
                                        <span className="owner-badge">{a.owner}</span>
                                      </div>
                                      <div className="expand-action-text">{a.action}</div>
                                    </div>
                                  )
                                })}
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
