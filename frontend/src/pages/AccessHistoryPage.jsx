import { AccessAdminFilters } from '../access/AccessAdminFilters.jsx'
import { AccessEventsTable } from '../access/AccessEventsTable.jsx'
import { ADMIN_FILTERS } from '../access/format.js'
import { listAccessHistory } from '../api/eventos.js'
import { canInspectAccesses, useAuth } from '../auth/useAuth.js'
import { CollectionControls } from '../components/CollectionControls.jsx'
import { Alert, EmptyState, Skeleton } from '../components/Feedback.jsx'
import { usePagedList, PAGE_SIZE } from '../hooks/usePagedList.js'

const NO_FILTERS = {}

export function AccessHistoryPage() {
  const { user } = useAuth()
  const administrative = canInspectAccesses(user)
  const page = usePagedList(listAccessHistory, 'eventos', administrative ? ADMIN_FILTERS : NO_FILTERS)

  return <section className="page-section" aria-labelledby="access-history-title">
    <div className="page-head"><div><p className="eyebrow">Accesos manuales</p>
      <h1 id="access-history-title">Historial de movimientos</h1>
      <p className="page-intro">{administrative
        ? 'Histórico autorizado de Eventos de Acceso. Las fechas de filtro corresponden a Bogotá.'
        : 'Resumen reducido de la jornada actual de Bogotá. La hora mostrada es aproximada.'}</p>
    </div><button type="button" className="btn btn-outline-secondary" onClick={page.retry}>
      Actualizar historial
    </button></div>

    {administrative && <AccessAdminFilters page={page} label="historial de accesos" />}
    <div className="results-panel"><div className="results-heading">
      <h2>Resultados</h2>
      {page.status === 'success' && <span className="muted">Página {Math.floor(page.offset / PAGE_SIZE) + 1}</span>}
    </div>
      {page.status === 'loading' && <Skeleton rows={5} />}
      {page.status === 'error' && <Alert message={page.error} onRetry={page.retry} />}
      {page.status === 'success' && <>
        {page.rows.length
          ? <AccessEventsTable rows={page.rows} reduced={!administrative}
            caption={`Historial de accesos, página ${Math.floor(page.offset / PAGE_SIZE) + 1}`} />
          : <EmptyState>No hay movimientos en esta página.</EmptyState>}
        <CollectionControls label="historial de accesos" offset={page.offset} count={page.rows.length}
          previous={page.previous} next={page.next} />
      </>}
    </div>
  </section>
}
