import { useState, useEffect, useCallback, useRef } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTip,
  ReferenceLine, Cell, ResponsiveContainer,
} from 'recharts'
import { DeploymentMatchRow } from '../types'
import { fetchDeploymentMatches } from '../api'

/* ─── constants ──────────────────────────────────────────────────── */

type GradeBand = 'All Grades' | 'IS Band' | 'DT Band' | 'DM Band' | 'DP Band' | 'BC Band' | 'LN Band' | 'Others'

const GRADE_BANDS: GradeBand[] = [
  'All Grades', 'IS Band', 'DT Band', 'DM Band', 'DP Band', 'BC Band', 'LN Band', 'Others',
]
const BAND_PARAM: Record<GradeBand, string> = {
  'All Grades': 'All', 'IS Band': 'IS Band', 'DT Band': 'DT Band',
  'DM Band': 'DM Band', 'DP Band': 'DP Band', 'BC Band': 'BC Band',
  'LN Band': 'LN Band', 'Others': 'Others',
}

const MONO = "'DM Mono', monospace"
const SORA = "'Sora', 'Inter', sans-serif"

const COL = {
  red: '#EF4444', amber: '#F59E0B', green: '#16A34A', blue: '#4361EE',
  text3: 'var(--text-3)', text4: 'var(--text-4)', border: 'var(--border-1)',
}

/* ─── types ──────────────────────────────────────────────────────── */

interface BarDatum {
  skill: string; pct: number; rawPct: number
  bench: number; demand: number; isSurplus: boolean; surplus: number
}
interface CardData {
  skill: string; bench: number; demand: number; gap: number; coverage: string
}

/* ─── helpers ────────────────────────────────────────────────────── */

function barColor(pct: number, isSurplus: boolean) {
  if (isSurplus) return COL.blue
  if (pct < 25)  return COL.red
  if (pct <= 80) return COL.amber
  return COL.green
}
function accentFor(cov: string) {
  if (cov === 'NONE') return COL.red
  if (cov === 'PARTIAL') return COL.amber
  return COL.green
}
function tooltipFor(cov: string) {
  if (cov === 'NONE')    return 'Recommended action: Initiate hiring or redeploy from surplus skills'
  if (cov === 'PARTIAL') return 'Recommended action: Monitor — check release pipeline for incoming bench'
  return 'Recommended action: Pause hiring — consider redeployment to gap skills'
}

/* ─── bar label ──────────────────────────────────────────────────── */

function makeBarLabel(data: BarDatum[]) {
  return function BarLabel(props: any) {
    const { x, y, width, height, index } = props
    const d = data[index]
    if (!d) return null
    const txt = d.isSurplus
      ? `${d.bench}/${d.demand}  +${d.surplus}`
      : `${d.bench}/${d.demand}  (${d.rawPct}%)`
    return (
      <text x={x + width + 6} y={y + height / 2 + 4}
        fontSize={9} fontFamily={MONO} fill={COL.text3}>{txt}</text>
    )
  }
}

/* ─── chart tooltip ──────────────────────────────────────────────── */

function ChartTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload as BarDatum
  return (
    <div style={{
      background: 'var(--card-bg)', border: `1px solid ${COL.border}`,
      borderRadius: 6, padding: '8px 12px', fontSize: 12,
      boxShadow: '0 4px 16px rgba(0,0,0,0.18)',
    }}>
      <div style={{ fontWeight: 700, color: 'var(--text-1)', marginBottom: 4, fontFamily: SORA }}>{d.skill}</div>
      <div style={{ color: COL.text3, fontFamily: MONO }}>{d.bench} bench / {d.demand} demand</div>
      <div style={{ fontFamily: MONO, fontWeight: 700, marginTop: 4, color: barColor(d.pct, d.isSurplus) }}>
        {d.isSurplus ? `+${d.surplus} surplus` : `${d.rawPct}% coverage`}
      </div>
    </div>
  )
}

/* ─── skill card ─────────────────────────────────────────────────── */

function SkillCard({ data, selected, onSelect }: {
  data: CardData; selected: boolean; onSelect: () => void
}) {
  const [hovered, setHovered] = useState(false)
  const accent = accentFor(data.coverage)
  const net = data.bench - data.demand
  const pct = data.demand === 0 ? 0 : Math.min(Math.round(data.bench / data.demand * 100), 100)

  return (
    <div
      onClick={onSelect}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: 'var(--card-bg)',
        border: `1px solid ${selected ? accent : 'rgba(0,0,0,0.08)'}`,
        borderLeft: `4px solid ${accent}`,
        borderRadius: 8,
        padding: '10px 12px',
        cursor: 'pointer',
        transition: 'transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s',
        transform: hovered ? 'translateY(-2px)' : 'translateY(0)',
        boxShadow: hovered ? '0 8px 20px rgba(0,0,0,0.13)' : '0 1px 3px rgba(0,0,0,0.06)',
        flexShrink: 0,
      }}
    >
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-1)', fontFamily: SORA, marginBottom: 6, lineHeight: 1.2 }}>
        {data.skill}
      </div>
      <div style={{ background: 'rgba(100,116,139,0.15)', borderRadius: 3, height: 5, marginBottom: 5, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: accent, borderRadius: 3, transition: 'width 0.4s ease' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 10, color: COL.text3, fontFamily: MONO }}>
          {data.bench}b · {data.demand}d · {pct}%
        </div>
        <div style={{ fontSize: 16, fontWeight: 800, fontFamily: MONO, lineHeight: 1, color: net >= 0 ? COL.green : COL.red }}>
          {net >= 0 ? `+${net}` : `${net}`}
        </div>
      </div>
      {selected && (
        <div style={{
          marginTop: 8, padding: '6px 8px',
          background: `${accent}15`, borderRadius: 4,
          fontSize: 10, color: 'var(--text-2)', lineHeight: 1.5,
          borderLeft: `2px solid ${accent}`,
        }}>
          💡 {tooltipFor(data.coverage)}
        </div>
      )}
    </div>
  )
}

/* ─── column ─────────────────────────────────────────────────────── */

function Column({ emoji, label, sub, accent, cards, selected, onSelect, pulsing }: {
  emoji: string; label: string; sub: string; accent: string
  cards: CardData[]; selected: string | null
  onSelect: (skill: string) => void; pulsing: boolean
}) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
      border: `1px solid ${COL.border}`, borderRadius: 10,
      outline: pulsing ? `2px solid ${accent}` : '2px solid transparent',
      transition: 'outline 0.2s ease',
    }}>
      {/* sticky header within this column's scroll container */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 2,
        background: 'var(--card-bg)',
        borderTop: `3px solid ${accent}`,
        borderBottom: `1px solid ${accent}30`,
        padding: '9px 12px 7px',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 13 }}>{emoji}</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: accent, fontFamily: SORA }}>{label}</span>
          <span style={{
            background: accent, color: '#fff',
            borderRadius: 10, padding: '1px 7px',
            fontSize: 10, fontFamily: MONO, fontWeight: 700,
          }}>{cards.length}</span>
        </div>
        <div style={{ fontSize: 10, color: COL.text4, marginTop: 1, paddingLeft: 19 }}>{sub}</div>
      </div>

      {/* scrollable card list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px', display: 'flex', flexDirection: 'column', gap: 7 }}>
        {cards.length === 0 ? (
          <div style={{
            background: `${accent}10`, border: `1px solid ${accent}30`,
            borderRadius: 8, padding: '14px 12px',
            display: 'flex', alignItems: 'flex-start', gap: 10,
          }}>
            <span style={{ fontSize: 16, flexShrink: 0 }}>
              {accent === COL.red ? '✅' : accent === COL.amber ? '✅' : '📋'}
            </span>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: COL.green, marginBottom: 3 }}>
                {accent === COL.red ? 'No critical gaps!' : accent === COL.amber ? 'No partial skills' : 'No covered skills yet'}
              </div>
              <div style={{ fontSize: 11, color: COL.text3, lineHeight: 1.4 }}>
                {accent === COL.red
                  ? 'All skills have at least some bench coverage.'
                  : accent === COL.amber
                  ? 'All demanded skills are either fully covered or have no bench.'
                  : 'No skills currently have full bench coverage.'}
              </div>
            </div>
          </div>
        ) : (
          cards.map(s => (
            <SkillCard key={s.skill} data={s}
              selected={selected === s.skill}
              onSelect={() => onSelect(s.skill)} />
          ))
        )}
      </div>
    </div>
  )
}

/* ─── main ───────────────────────────────────────────────────────── */

export default function SkillGap() {
  const [band, setBand]       = useState<GradeBand>('All Grades')
  const [matches, setMatches] = useState<DeploymentMatchRow[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)
  const [search, setSearch]   = useState('')
  const [pulse, setPulse]     = useState<'none' | 'partial' | 'full' | null>(null)

  const load = useCallback((b: GradeBand) => {
    setLoading(true)
    fetchDeploymentMatches(BAND_PARAM[b])
      .then(d => { setMatches(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  useEffect(() => { load('All Grades') }, [load])

  function changeBand(b: GradeBand) {
    setBand(b); setSelected(null); setSearch(''); load(b)
  }

  function jumpTo(col: 'none' | 'partial' | 'full') {
    setPulse(col)
    setTimeout(() => setPulse(null), 900)
  }

  /* ── derived data ── */
  const q        = search.trim().toLowerCase()
  const filtered = q ? matches.filter(m => m.skill.toLowerCase().includes(q)) : matches

  const total    = matches.length
  const critical = matches.filter(m => m.coverage === 'NONE').length
  const partial  = matches.filter(m => m.coverage === 'PARTIAL').length
  const wellCov  = matches.filter(m => m.coverage === 'FULL').length

  const barData: BarDatum[] = filtered
    .map(m => {
      const rawPct    = m.open_demand_count === 0 ? 0
        : Math.round(m.matched_bench_count / m.open_demand_count * 100)
      const isSurplus = m.matched_bench_count > m.open_demand_count
      return {
        skill: m.skill, pct: Math.min(rawPct, 150), rawPct,
        bench: m.matched_bench_count, demand: m.open_demand_count,
        isSurplus, surplus: Math.max(0, m.matched_bench_count - m.open_demand_count),
      }
    })
    .sort((a, b) => a.pct - b.pct)
    .slice(0, 20)

  const xMax = barData.length ? Math.max(...barData.map(d => d.pct), 110) : 110
  const chartInnerH = Math.max(barData.length * 32 + 20, 80)

  const noneSkills: CardData[] = filtered
    .filter(m => m.coverage === 'NONE')
    .map(m => ({ skill: m.skill, bench: 0, demand: m.open_demand_count, gap: -m.open_demand_count, coverage: 'NONE' }))
    .sort((a, b) => a.gap - b.gap)

  const partSkills: CardData[] = filtered
    .filter(m => m.coverage === 'PARTIAL')
    .map(m => ({ skill: m.skill, bench: m.matched_bench_count, demand: m.open_demand_count, gap: m.matched_bench_count - m.open_demand_count, coverage: 'PARTIAL' }))
    .sort((a, b) => a.gap - b.gap)

  const fullSkills: CardData[] = filtered
    .filter(m => m.coverage === 'FULL')
    .map(m => ({ skill: m.skill, bench: m.matched_bench_count, demand: m.open_demand_count, gap: m.matched_bench_count - m.open_demand_count, coverage: 'FULL' }))
    .sort((a, b) => b.gap - a.gap)

  const renderBarLabel = makeBarLabel(barData)

  function toggleSelected(skill: string) {
    setSelected(p => p === skill ? null : skill)
  }

  return (
    <section style={{ position: 'relative' }}>

      {/* ── Title (not sticky) ── */}
      <h2 className="section-title" style={{ marginBottom: 8 }}>
        <span className="section-title-icon">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round">
            <rect x="1" y="1" width="6" height="6" rx="1"/>
            <rect x="9" y="1" width="6" height="6" rx="1"/>
            <rect x="1" y="9" width="6" height="6" rx="1"/>
            <rect x="9" y="9" width="6" height="6" rx="1"/>
          </svg>
        </span>
        Skill Gap Analysis
        <span className="section-count">real data · deployment-matches</span>
      </h2>

      {/* ── ROW 1: Sticky search + grade filter ── */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 20,
        background: 'var(--card-bg)',
        borderBottom: `1px solid ${COL.border}`,
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        padding: '10px 0 8px',
        marginBottom: 14,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          {/* Search */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 7,
            background: 'var(--input-bg, rgba(0,0,0,0.04))',
            border: `1px solid ${COL.border}`, borderRadius: 7,
            padding: '5px 10px', minWidth: 200,
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
              style={{ color: COL.text4, flexShrink: 0 }}>
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              type="text"
              placeholder="Search skills…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{
                border: 'none', outline: 'none', background: 'transparent',
                fontSize: 12, color: 'var(--text-1)', width: '100%', fontFamily: 'inherit',
              }}
            />
            {search && (
              <button onClick={() => setSearch('')}
                style={{ border: 'none', background: 'none', cursor: 'pointer', color: COL.text4, fontSize: 13, padding: 0 }}>
                ✕
              </button>
            )}
          </div>

          {/* Grade band buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 11, color: COL.text4, whiteSpace: 'nowrap' }}>Grade Band:</span>
            {GRADE_BANDS.map(b => (
              <button key={b}
                className={`sg-filter-btn${band === b ? ' sg-filter-active' : ''}`}
                onClick={() => changeBand(b)}
                style={{ fontSize: 11, padding: '3px 9px' }}>
                {b}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: COL.text4, fontSize: 13 }}>
          Loading skill coverage…
        </div>
      ) : matches.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: COL.text4, fontSize: 13 }}>
          No demand data for this grade band.
        </div>
      ) : (
        <>
          {/* ── ROW 2: Compact summary cards ── */}
          <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
            {[
              { val: total,    label: 'Total',         color: 'var(--text-1)' },
              { val: critical, label: 'Critical Gaps', color: COL.red   },
              { val: partial,  label: 'Partial',       color: COL.amber },
              { val: wellCov,  label: 'Covered',       color: COL.green },
            ].map(({ val, label, color }) => (
              <div key={label} style={{
                flex: 1, background: 'var(--card-bg)',
                border: `1px solid ${COL.border}`, borderRadius: 8,
                padding: '7px 14px', display: 'flex', alignItems: 'center', gap: 10,
              }}>
                <span style={{ fontSize: 22, fontWeight: 800, fontFamily: MONO, color, lineHeight: 1 }}>{val}</span>
                <span style={{ fontSize: 11, color: COL.text3, lineHeight: 1.2 }}>{label}</span>
              </div>
            ))}
          </div>

          {/* ── Quick nav ── */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <span style={{ fontSize: 11, color: COL.text4 }}>Quick view:</span>
            {[
              { col: 'none'    as const, emoji: '🔴', count: noneSkills.length, label: 'Critical', color: COL.red   },
              { col: 'partial' as const, emoji: '🟡', count: partSkills.length, label: 'Partial',  color: COL.amber },
              { col: 'full'    as const, emoji: '🟢', count: fullSkills.length, label: 'Covered',  color: COL.green },
            ].map(({ col, emoji, count, label, color }) => (
              <button key={col} onClick={() => jumpTo(col)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 5,
                  background: `${color}12`, border: `1px solid ${color}40`,
                  borderRadius: 20, padding: '4px 12px',
                  cursor: 'pointer', fontSize: 12, color,
                  fontWeight: 600, transition: 'background 0.15s',
                }}>
                <span>{emoji}</span>
                <span style={{ fontFamily: MONO, fontWeight: 700 }}>{count}</span>
                <span>{label}</span>
              </button>
            ))}
          </div>

          {/* ── ROW 3: Split view ── */}
          <div style={{ display: 'flex', gap: 14, height: 520 }}>

            {/* Left: Bar chart (40%) */}
            <div style={{
              width: '40%', flexShrink: 0,
              background: 'var(--card-bg)',
              border: `1px solid ${COL.border}`,
              borderRadius: 10, display: 'flex', flexDirection: 'column', overflow: 'hidden',
            }}>
              {/* chart header — sticky within left panel */}
              <div style={{
                padding: '12px 16px 8px', flexShrink: 0,
                borderBottom: `1px solid ${COL.border}`,
              }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-1)', fontFamily: SORA }}>
                  Coverage by Skill
                </div>
                <div style={{ fontSize: 10, color: COL.text4, marginTop: 2 }}>
                  Worst first · top 20 · dashed = 100% demand met
                </div>
              </div>

              {/* scrollable chart area */}
              <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', padding: '8px 4px 8px 0' }}>
                {barData.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px 16px', color: COL.text4, fontSize: 12 }}>
                    No skills match your search.
                  </div>
                ) : (
                  <div style={{ width: '100%', height: chartInnerH }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={barData}
                        layout="vertical"
                        margin={{ top: 4, right: 120, bottom: 4, left: 0 }}
                        barSize={14}
                      >
                        <XAxis type="number" domain={[0, xMax]}
                          tickFormatter={v => `${v}%`}
                          tick={{ fontSize: 9, fontFamily: MONO, fill: COL.text4 }}
                          axisLine={false} tickLine={false} />
                        <YAxis type="category" dataKey="skill" width={140}
                          tick={{ fontSize: 10, fill: 'var(--text-2)' }}
                          axisLine={false} tickLine={false} />
                        <RechartsTip content={<ChartTooltip />} cursor={{ fill: 'rgba(148,163,184,0.07)' }} />
                        <ReferenceLine x={100} stroke="#64748B" strokeDasharray="5 3" strokeWidth={1.5} />
                        <Bar dataKey="pct" radius={[0, 3, 3, 0]} label={renderBarLabel}>
                          {barData.map((d, i) => (
                            <Cell key={i} fill={barColor(d.pct, d.isSurplus)} fillOpacity={0.88} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* legend */}
              <div style={{ padding: '8px 14px', borderTop: `1px solid ${COL.border}`, display: 'flex', gap: 14, flexWrap: 'wrap', flexShrink: 0 }}>
                {[
                  { c: COL.red,   t: '<25% critical' },
                  { c: COL.amber, t: '25-80% partial' },
                  { c: COL.green, t: '>80% covered'  },
                  { c: COL.blue,  t: 'surplus'        },
                ].map(({ c, t }) => (
                  <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10, color: COL.text3 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: c, display: 'inline-block', flexShrink: 0 }} />
                    {t}
                  </div>
                ))}
              </div>
            </div>

            {/* Right: Three columns (60%) */}
            <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, minWidth: 0 }}>
              <Column
                emoji="🔴" label="Critical Gaps" sub="NONE — hire urgently"
                accent={COL.red} cards={noneSkills}
                selected={selected} onSelect={toggleSelected}
                pulsing={pulse === 'none'}
              />
              <Column
                emoji="🟡" label="Partial" sub="PARTIAL — monitor"
                accent={COL.amber} cards={partSkills}
                selected={selected} onSelect={toggleSelected}
                pulsing={pulse === 'partial'}
              />
              <Column
                emoji="🟢" label="Covered" sub="FULL — consider freeze"
                accent={COL.green} cards={fullSkills}
                selected={selected} onSelect={toggleSelected}
                pulsing={pulse === 'full'}
              />
            </div>

          </div>
        </>
      )}
    </section>
  )
}
