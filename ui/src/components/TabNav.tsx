interface Props {
  active: string
  onChange: (tab: string) => void
}

const TABS = [
  { id: 'summary',  label: 'Bench Summary' },
  { id: 'forecast', label: '30/60/90-Day Forecast' },
  { id: 'alerts',   label: 'Threshold Alerts' },
  { id: 'freeze',   label: 'Hiring Freeze Advisory' },
]

export default function TabNav({ active, onChange }: Props) {
  return (
    <nav className="tab-nav">
      {TABS.map((t) => (
        <button
          key={t.id}
          className={`tab-btn${active === t.id ? ' active' : ''}`}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </nav>
  )
}
