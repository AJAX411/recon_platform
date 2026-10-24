import { PAGE_SIZE } from '../hooks/usePagedList.js'

export function CollectionControls({ offset, count, previous, next, label }) {
  return <nav className="pagination-controls" aria-label={`Paginación de ${label}`}>
    <button type="button" className="btn btn-outline-secondary" disabled={offset === 0} onClick={previous}>Anterior</button>
    <button type="button" className="btn btn-outline-secondary" disabled={count < PAGE_SIZE || offset + PAGE_SIZE > 1_000_000} onClick={next}>Siguiente</button>
  </nav>
}
