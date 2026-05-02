import { useState } from 'react'
import { ActionItem, FreezeRow } from '../types'

interface Props {
  data: FreezeRow[]
  actions?: ActionItem[]
}

type FilterMode = 'all' | 'yes' | 'no'

export default function HiringFreeze({ data, actions = [] }: Props) {
  const [expanded, setExpanded]   = useState<Set<string>>(new Set())
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [filter, setFilter]       = useState<FilterMode>('all')

  const freezeCount   = data.filter((r) => r.freeze_recommended).length
  const noFreezeCount = data.length - freezeCount
  const freezeRows    = data.filter((r) => r.freeze_recommended)
  const avgSurplus    = freezeRows.length
    ? Math.round(freezeRows.reduce((a, r) => a + r.supply_surplus, 0) / freezeRows.length)
    : 0

  const displayed = filter === 'yes'
    ? data.filter((r) => r.freeze_recommended)
    : filter === 'no'
      ? data.filter((r) => !r.freeze_recommended)
      : data

  const actionsBySkill: Record<string, ActionItem[]> = {}
  for (const a of actions) {
    if (a.rule === 'R4' && a.skill) {
      if (!actionsBySkill[a.skill]) actionsBySkill[a.skill] = []
      actionsBySkill[a.skill].push(a)
    }
  }

  function toggle(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  function copyEmail(key: string, body: string) {
    navigator.clipboard.writeText(body).then(() => {
      setCopiedKey(key)
      setTimeout(() => setCopiedKey(null), 2000)
    })
  }

  return (
    <section>
      <h2 className="section-title">
        <span className="section-title-icon">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="8" y1="1" x2="8" y2="15" />
            <line x1="1" y1="8" x2="15" y2="8" />
            <line x1="3.17" y1="3.17" x2="12.83" y2="12.83" />
            <line x1="12.83" y1="3.17" x2="3.17" y2="12.83" />
          </svg>
        </span>
        Hiring Freeze Advisory
        <span className="section-count">{data.length} skills · {freezeCount} freeze recommended</span>
      </h2>

      <div className="freeze-header-stats">
        <div className="freeze-stat freeze-stat-freeze">
          <div className="freeze-stat-val">{freezeCount}</div>
          <div className="freeze-stat-lbl">Freeze Recommended</div>
        </div>
        <div className="freeze-stat">
          <div className="freeze-stat-val">{noFreezeCount}</div>
          <div className="freeze-stat-lbl">No Freeze Needed</div>
        </div>
        <div className="freeze-stat" style={{ borderColor: 'rgba(16,185,129,.2)', background: 'rgba(16,185,129,.07)' }}>
          <div className="freeze-stat-val" style={{ color: 'var(--green)' }}>{data.length}</div>
          <div className="freeze-stat-lbl">Total Skills Tracked</div>
        </div>
        <div className="freeze-stat" style={{ borderColor: 'rgba(245,158,11,.2)', background: 'rgba(245,158,11,.07)' }}>
          <div className="freeze-stat-val" style={{ color: 'var(--amber)' }}>+{avgSurplus}</div>
          <div className="freeze-stat-lbl">Avg Surplus (Frozen)</div>
        </div>
      </div>

      {/* YES / NO filter */}
      <div className="freeze-filter-bar">
        <span className="freeze-filter-label">Show:</span>
        <button
          className={`freeze-filter-btn${filter === 'all' ? ' active-all' : ''}`}
          onClick={() => setFilter('all')}
        >All</button>
        <button
          className={`freeze-filter-btn${filter === 'yes' ? ' active-yes' : ''}`}
          onClick={() => setFilter('yes')}
        >Freeze: YES</button>
        <button
          className={`freeze-filter-btn${filter === 'no' ? ' active-no' : ''}`}
          onClick={() => setFilter('no')}
        >Freeze: NO</button>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-scroll" style={{ border: 'none', borderRadius: 0 }}>
          <table>
            <thead>
              <tr>
                <th>Skill</th>
                <th className="num">Supply</th>
                <th className="num">Demand</th>
                <th className="num">Surplus / Deficit</th>
                <th className="num">Avg Rating</th>
                <th>Freeze?</th>
                <th>LLM Narrative</th>
              </tr>
            </thead>
            <tbody>
              {displayed.map((row) => {
                const hasActions = (actionsBySkill[row.skill]?.length ?? 0) > 0
                const isOpen = expanded.has(row.skill)
                return (
                  <>
                    <tr
                      key={row.skill}
                      className={`${row.freeze_recommended ? 'r-freeze' : ''}${hasActions ? ' expand-trigger' : ''}`}
                      onClick={hasActions ? () => toggle(row.skill) : undefined}
                    >
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <strong className="skill-name">{row.skill}</strong>
                          {hasActions && (
                            <span className={`expand-chevron${isOpen ? ' open' : ''}`}>▶</span>
                          )}
                        </div>
                      </td>
                      <td className="num"><span className="num-chip">{row.total_supply}</span></td>
                      <td className="num" style={{ color: 'var(--text-3)' }}>{row.open_demand_count}</td>
                      <td className="num">
                        {row.supply_surplus > 0
                          ? <span className="surplus-pos">+{row.supply_surplus}</span>
                          : <span className="surplus-neg">{row.supply_surplus}</span>}
                      </td>
                      <td className="num">
                        {row.avg_skill_rating != null
                          ? <span className="star-rating"><span className="star">★</span>{row.avg_skill_rating.toFixed(1)}</span>
                          : <span style={{ color: 'var(--text-4)' }}>—</span>}
                      </td>
                      <td>
                        <span className={`badge ${row.freeze_recommended ? 'b-freeze' : 'b-nofreeze'}`}>
                          {row.freeze_recommended ? 'YES' : 'NO'}
                        </span>
                      </td>
                      <td className="narrative">{row.llm_narrative ?? row.advisory_note}</td>
                    </tr>
                    {hasActions && (
                      <tr key={`${row.skill}-expand`} className="expand-row">
                        <td colSpan={7}>
                          <div className={`expand-detail${isOpen ? ' open' : ''}`}>
                            <div className="expand-detail-inner">
                              <div className="expand-actions-list">
                                {actionsBySkill[row.skill].map((a, i) => {
                                  const emailKey = `${row.skill}-${i}`
                                  const css = a.priority === 'IMMEDIATE' ? 'IMMEDIATE' : a.priority === '7-DAY' ? 'DAY7' : 'DAY30'
                                  return (
                                    <div key={i} className="expand-action-item" style={{ flexDirection: 'column', gap: 10 }}>
                                      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                                        <div className="expand-action-meta">
                                          <span className="rule-tag">{a.rule}</span>
                                          <span className={`priority-pill ${css}`}>{a.priority}</span>
                                          <span className="owner-badge">{a.owner}</span>
                                        </div>
                                        <div className="expand-action-text">{a.action}</div>
                                      </div>
                                      {a.hr_email && (
                                        <div className="email-block">
                                          <div className="email-header">
                                            <span className="email-label">Draft HR Communication</span>
                                            <button
                                              className="copy-btn"
                                              onClick={(e) => { e.stopPropagation(); copyEmail(emailKey, a.hr_email!.body) }}
                                            >
                                              {copiedKey === emailKey ? '✓ Copied!' : 'Copy'}
                                            </button>
                                          </div>
                                          <div className="email-subject">
                                            <strong>Subject:</strong> {a.hr_email.subject}
                                          </div>
                                          <pre className="email-body">{a.hr_email.body}</pre>
                                        </div>
                                      )}
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
