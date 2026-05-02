import { CoverageLevel, DeploymentMatchRow } from '../types'

interface Props { data: DeploymentMatchRow[] }

const COV_BADGE: Record<CoverageLevel, string> = {
  FULL:    'cov-full',
  PARTIAL: 'cov-partial',
  NONE:    'cov-none',
}
const COV_ROW: Record<CoverageLevel, string> = {
  FULL:    '',
  PARTIAL: 'r-medium',
  NONE:    'r-critical',
}

export default function DeploymentMatches({ data }: Props) {
  const full    = data.filter((r) => r.coverage === 'FULL').length
  const partial = data.filter((r) => r.coverage === 'PARTIAL').length
  const none    = data.filter((r) => r.coverage === 'NONE').length

  return (
    <section>
      <h2 className="section-title">
        <span className="section-title-icon">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="5" cy="8" r="3" />
            <circle cx="11" cy="8" r="3" />
            <line x1="8" y1="5.5" x2="8" y2="10.5" />
          </svg>
        </span>
        Deployment Matches
        <span className="section-count">{data.length} skills tracked</span>
      </h2>

      {/* Summary cards */}
      <div className="freeze-header-stats" style={{ marginBottom: 20 }}>
        <div className="freeze-stat" style={{ borderColor: 'rgba(239,68,68,.2)', background: 'rgba(239,68,68,.06)' }}>
          <div className="freeze-stat-val" style={{ color: 'var(--red)' }}>{none}</div>
          <div className="freeze-stat-lbl">No Coverage (NONE)</div>
        </div>
        <div className="freeze-stat" style={{ borderColor: 'rgba(245,158,11,.2)', background: 'rgba(245,158,11,.06)' }}>
          <div className="freeze-stat-val" style={{ color: 'var(--amber)' }}>{partial}</div>
          <div className="freeze-stat-lbl">Partial Coverage</div>
        </div>
        <div className="freeze-stat" style={{ borderColor: 'rgba(45,122,58,.2)', background: 'var(--green-dim)' }}>
          <div className="freeze-stat-val" style={{ color: 'var(--green)' }}>{full}</div>
          <div className="freeze-stat-lbl">Full Coverage</div>
        </div>
        <div className="freeze-stat">
          <div className="freeze-stat-val">{data.length}</div>
          <div className="freeze-stat-lbl">Skills in Demand</div>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-scroll" style={{ border: 'none', borderRadius: 0 }}>
          <table>
            <thead>
              <tr>
                <th>Skill</th>
                <th className="num">Open Demand</th>
                <th className="num">Matched Bench</th>
                <th className="num">Match Rate %</th>
                <th>Coverage</th>
                <th className="num">Gap</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.skill} className={COV_ROW[row.coverage]}>
                  <td><strong className="skill-name">{row.skill}</strong></td>
                  <td className="num"><span className="num-chip">{row.open_demand_count}</span></td>
                  <td className="num"><span className="num-chip">{row.matched_bench_count}</span></td>
                  <td className="num">
                    <span style={{
                      fontFamily: 'DM Mono, monospace', fontWeight: 600,
                      color: row.match_rate_pct >= 100 ? 'var(--green)'
                           : row.match_rate_pct > 0   ? 'var(--amber)'
                           : 'var(--red)',
                    }}>
                      {row.match_rate_pct.toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${COV_BADGE[row.coverage]}`}>
                      {row.coverage}
                    </span>
                  </td>
                  <td className="num">
                    {row.gap > 0
                      ? <span className="surplus-pos">+{row.gap}</span>
                      : <span className="surplus-neg">{row.gap}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
