import { useState } from 'react'
import { ActionItem, RmNudge } from '../types'

interface Props {
  data: ActionItem[]
  rmNudges?: RmNudge[]
}

const PRIORITY_ORDER = ['IMMEDIATE', '7-DAY', '30-DAY'] as const

const PRIORITY_CSS: Record<string, string> = {
  'IMMEDIATE': 'IMMEDIATE',
  '7-DAY':     'DAY7',
  '30-DAY':    'DAY30',
}

function RmNudgeCard({ nudge }: { nudge: RmNudge }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied]     = useState(false)

  function handleCopy() {
    const text = `Subject: ${nudge.email_subject}\n\n${nudge.email_body}`
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const urgencyClass = nudge.urgency === 'HIGH' ? 'urgency-high-badge' : 'urgency-medium-badge'

  return (
    <div className={`rm-nudge-card urgency-${nudge.urgency.toLowerCase()}`}>
      <div className="rm-nudge-header" onClick={() => setExpanded(e => !e)}>
        <span className="rm-nudge-name">{nudge.rm_name}</span>
        <span className="rm-nudge-count">
          {nudge.employee_count} employee{nudge.employee_count !== 1 ? 's' : ''}
        </span>
        <span className={urgencyClass}>{nudge.urgency}</span>
        <span className="expand-chevron" style={{ marginLeft: 4, color: 'var(--text-4)', fontSize: 10 }}>
          {expanded ? '▼' : '▶'}
        </span>
      </div>

      {expanded && (
        <div className="rm-nudge-body">
          <div className="email-block">
            <div className="email-header">
              <span className="email-label">Draft RM Communication</span>
              <button className="copy-btn" onClick={handleCopy}>
                {copied ? '✓ Copied!' : 'Copy Email'}
              </button>
            </div>
            <div className="email-subject"><strong>Subject:</strong> {nudge.email_subject}</div>
            <pre className="email-body">{nudge.email_body}</pre>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ActionCards({ data, rmNudges = [] }: Props) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  const byPriority = PRIORITY_ORDER
    .map((p) => ({ priority: p, items: data.filter((a) => a.priority === p) }))
    .filter((g) => g.items.length > 0)

  function copyEmail(key: string, text: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedKey(key)
      setTimeout(() => setCopiedKey(null), 2000)
    })
  }

  let cardIdx = 0

  return (
    <section>
      <h2 className="section-title">
        Recommended Actions
        <span className="section-count">{data.length} actions</span>
      </h2>

      {rmNudges.length > 0 && (
        <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--text-4)' }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
            <polyline points="22,6 12,13 2,6"/>
          </svg>
          Scroll down for RM Nudge emails
        </div>
      )}

      {byPriority.map(({ priority, items }) => (
        <div key={priority} className="priority-group">
          <div className="priority-group-label">{priority}</div>
          <div className="action-cards-list">
            {items.map((item, i) => {
              const idx = cardIdx++
              const emailKey = item.skill ?? item.org_slice ?? `${item.rule}-${i}`
              const css = PRIORITY_CSS[priority]
              return (
                <div
                  key={i}
                  className={`action-card ${css}`}
                  style={{ animationDelay: `${idx * 60}ms` }}
                >
                  <div className="action-card-header">
                    <span className="rule-tag">{item.rule}</span>
                    <span className="owner-badge">{item.owner}</span>
                    <span className={`priority-pill ${css}`}>{priority}</span>
                  </div>
                  <div className="action-text">{item.action}</div>
                  <div className="action-rationale">{item.rationale}</div>

                  {item.hr_email && (
                    <div className="email-block">
                      <div className="email-header">
                        <span className="email-label">📧 Draft HR Communication</span>
                        <button
                          className="copy-btn"
                          onClick={() => copyEmail(emailKey, item.hr_email!.body)}
                        >
                          {copiedKey === emailKey ? '✓ Copied!' : 'Copy'}
                        </button>
                      </div>
                      <div className="email-subject">
                        <strong>Subject:</strong> {item.hr_email.subject}
                      </div>
                      <pre className="email-body">{item.hr_email.body}</pre>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}

      {rmNudges.length > 0 && (
        <div className="rm-nudges-section">
          <h2 className="section-title" style={{ marginTop: 32 }}>
            RM Nudges
            <span className="section-count">{rmNudges.length} RM{rmNudges.length !== 1 ? 's' : ''}</span>
          </h2>
          <div className="rm-nudge-cards-list">
            {rmNudges.map((nudge, i) => (
              <RmNudgeCard key={i} nudge={nudge} />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
