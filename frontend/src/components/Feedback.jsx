export function Alert({ message, tone = 'danger', onRetry }) {
  if (!message) return null
  return <div className={`alert alert-${tone}`} role={tone === 'danger' ? 'alert' : 'status'}>
    {message} {onRetry && <button type="button" className="btn btn-sm btn-outline-dark ms-2" onClick={onRetry}>Reintentar</button>}
  </div>
}

export function Skeleton({ rows = 3 }) {
  return <div role="status" aria-label="Cargando información" className="skeleton-group">
    {Array.from({ length: rows }, (_, index) => <div key={index} className="skeleton-line" />)}
    <span className="visually-hidden">Cargando información</span>
  </div>
}

export function EmptyState({ children }) {
  return <div className="empty-state" role="status">{children}</div>
}
