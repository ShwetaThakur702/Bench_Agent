export default function Skeleton() {
  return (
    <div className="skeleton-container">
      <div className="skeleton-bar" style={{ height: 32, width: '30%', marginBottom: 20 }} />
      <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr 1fr 1fr', gap: 14, marginBottom: 28 }}>
        <div className="skeleton-bar" style={{ height: 130 }} />
        <div className="skeleton-bar" style={{ height: 130 }} />
        <div className="skeleton-bar" style={{ height: 130 }} />
        <div className="skeleton-bar" style={{ height: 130 }} />
      </div>
      <div className="skeleton-bar" style={{ height: 32, width: '25%', marginBottom: 16 }} />
      <div className="skeleton-bar" style={{ height: 64, marginBottom: 10 }} />
      <div className="skeleton-bar" style={{ height: 64, marginBottom: 10 }} />
      <div className="skeleton-bar" style={{ height: 64, marginBottom: 10 }} />
      <div className="skeleton-bar" style={{ height: 64, marginBottom: 10 }} />
    </div>
  )
}
