export function StatusBadge({ estado }) {
  return <span className={`status-pill ${estado === 'ACTIVO' ? 'active' : 'inactive'}`}>{estado}</span>
}
