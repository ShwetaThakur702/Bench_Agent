interface Props {
  offline: boolean
  lastUpdated: string | null
}

export default function Header({ offline, lastUpdated }: Props) {
  return (
    <header className="app-header">
      <div>
        <div className="header-title">Bench Agent Dashboard</div>
        <div className="header-sub">Resource Management Intelligence — Advisory Only</div>
      </div>
      <div className="header-right">
        <span className={`banner ${offline ? 'banner-offline' : 'banner-live'}`}>
          {offline ? '⚠ API Offline — Static Preview' : '✓ Live data from API'}
        </span>
        {lastUpdated && (
          <span className="timestamp">Updated: {lastUpdated}</span>
        )}
      </div>
    </header>
  )
}
