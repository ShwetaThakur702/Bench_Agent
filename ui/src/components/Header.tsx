interface Props {
  offline: boolean
  lastUpdated: string | null
  dark: boolean
  onToggleDark: () => void
  onOpenDailyReport: () => void
  onOpenAgenda: () => void
  onDownloadExcel: () => void
}

export default function Header({ offline, lastUpdated, dark, onToggleDark, onOpenDailyReport, onOpenAgenda, onDownloadExcel }: Props) {
  return (
    <header className="app-header">
      <div className="header-logo">
        <div className="header-logo-mark" title="BenchAgent">
          <svg viewBox="0 0 24 24">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
        </div>
        <div className="header-wordmark">
          <div className="header-title">
            <span className="brand-bench">Bench</span>
            <span className="brand-agent">Agent</span>
          </div>
          <div className="header-sub">Resource Management Intelligence</div>
        </div>
      </div>

      <div className="header-right">
        <button className="agenda-btn" onClick={onDownloadExcel} title="Download Excel dashboard">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Excel Report
        </button>

        <button className="agenda-btn" onClick={onOpenAgenda}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
            <line x1="8" y1="14" x2="16" y2="14"/>
            <line x1="8" y1="18" x2="13" y2="18"/>
          </svg>
          Meeting Agenda
        </button>

        <button className="daily-report-btn" onClick={onOpenDailyReport}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
          Daily Report
        </button>

        <span className={`status-chip ${offline ? 'status-chip-offline' : 'status-chip-live'}`}>
          <span className="status-dot" />
          {offline ? 'Offline' : 'Live'}
        </span>

        {lastUpdated && <span className="timestamp">{lastUpdated}</span>}

        <button
          className="dark-toggle"
          onClick={onToggleDark}
          aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {dark ? (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="5" />
              <line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
              <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
            </svg>
          ) : (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          )}
          <div className="toggle-track">
            <div className="toggle-knob" />
          </div>
          <span>{dark ? 'Light' : 'Dark'}</span>
        </button>
      </div>
    </header>
  )
}
