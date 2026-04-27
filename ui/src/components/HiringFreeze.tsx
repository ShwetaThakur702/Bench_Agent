import { FreezeRow } from '../types'

interface Props { data: FreezeRow[] }

export default function HiringFreeze({ data }: Props) {
  const freezeCount = data.filter((r) => r.freeze_recommended).length

  return (
    <section>
      <h2 className="section-title">
        Hiring Freeze Advisory
        <span className="section-count">
          {data.length} skills · {freezeCount} freeze recommended
        </span>
      </h2>
      <div className="card">
        <div className="table-scroll">
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
              {data.map((row) => (
                <tr key={row.skill} className={row.freeze_recommended ? 'r-freeze' : ''}>
                  <td><strong>{row.skill}</strong></td>
                  <td className="num">{row.total_supply}</td>
                  <td className="num">{row.open_demand_count}</td>
                  <td className="num">
                    {row.supply_surplus > 0
                      ? <span className="surplus-pos">+{row.supply_surplus}</span>
                      : <span className="surplus-neg">{row.supply_surplus}</span>}
                  </td>
                  <td className="num">
                    {row.avg_skill_rating != null ? row.avg_skill_rating.toFixed(1) : '—'}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <span className={`badge ${row.freeze_recommended ? 'b-freeze' : 'b-nofreeze'}`}>
                      {row.freeze_recommended ? 'YES' : 'NO'}
                    </span>
                  </td>
                  <td className="narrative">
                    {row.llm_narrative ?? row.advisory_note}
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
