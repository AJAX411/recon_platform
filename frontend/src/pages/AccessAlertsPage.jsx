import { useEffect, useState } from 'react'
import { AccessAdminFilters } from '../access/AccessAdminFilters.jsx'
import { AccessEventsTable } from '../access/AccessEventsTable.jsx'
import { ADMIN_FILTERS, INCIDENCE_LABELS } from '../access/format.js'
import { getAccessAlertCounts, listAccessAlerts } from '../api/eventos.js'
import { canInspectAccesses, useAuth } from '../auth/useAuth.js'
import { CollectionControls } from '../components/CollectionControls.jsx'
import { Alert, EmptyState, Skeleton } from '../components/Feedback.jsx'
import { usePagedList, PAGE_SIZE } from '../hooks/usePagedList.js'

function OperatorAlerts() {
  const { expire } = useAuth()
  const [counts, setCounts] = useState({})
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setStatus('loading')
    setError('')
    getAccessAlertCounts(controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return
        setCounts(response.conteos_por_incidencia)
        setStatus('success')
      }).catch((failure) => {
        if (controller.signal.aborted) return
        if (failure.status === 401) expire()
        else { setError(failure.message); setStatus('error') }
      })
    return () => controller.abort()
  }, [revision, expire])

  const refresh = () => setRevision((value) => value + 1)
  return <section className="page-section" aria-labelledby="access-alerts-title">
    <div className="page-head"><div><p className="eyebrow">Accesos manuales</p>
      <h1 id="access-alerts-title">Alertas de la jornada</h1>
      <p className="page-intro">Conteos por tipo de incidencia del día actual en America/Bogota, sin datos personales.</p>
    </div><button type="button" className="btn btn-outline-secondary" onClick={refresh}>Actualizar alertas</button></div>
    <div className="results-panel">
      <h2>Conteos de incidencias</h2>
      {status === 'loading' && <Skeleton rows={3} />}
      {status === 'error' && <Alert message={error} onRetry={refresh} />}
      {status === 'success' && (Object.keys(counts).length
        ? <dl className="access-counts">{Object.entries(counts).map(([type, count]) =>
          <div key={type}><dt>{INCIDENCE_LABELS[type] || type}</dt><dd>{count}</dd></div>)}</dl>
        : <EmptyState>No hay incidencias en la jornada actual.</EmptyState>)}
    </div>
  </section>
}

function AdministrativeAlerts() {
  const page = usePagedList(listAccessAlerts, 'alertas', ADMIN_FILTERS)
  return <section className="page-section" aria-labelledby="access-alerts-title">
    <div className="page-head"><div><p className="eyebrow">Accesos manuales</p>
      <h1 id="access-alerts-title">Alertas e incidencias</h1>
      <p className="page-intro">Eventos con incidencia consultables según los permisos administrativos.</p>
    </div><button type="button" className="btn btn-outline-secondary" onClick={page.retry}>Actualizar alertas</button></div>
    <AccessAdminFilters page={page} label="alertas de acceso" />
    <div className="results-panel"><div className="results-heading">
      <h2>Incidencias</h2>
      {page.status === 'success' && <span className="muted">Página {Math.floor(page.offset / PAGE_SIZE) + 1}</span>}
    </div>
      {page.status === 'loading' && <Skeleton rows={5} />}
      {page.status === 'error' && <Alert message={page.error} onRetry={page.retry} />}
      {page.status === 'success' && <>
        {page.rows.length
          ? <AccessEventsTable rows={page.rows} reduced={false}
            caption={`Alertas de acceso, página ${Math.floor(page.offset / PAGE_SIZE) + 1}`} />
          : <EmptyState>No hay incidencias en esta página.</EmptyState>}
        <CollectionControls label="alertas de acceso" offset={page.offset} count={page.rows.length}
          previous={page.previous} next={page.next} />
      </>}
    </div>
  </section>
}

export function AccessAlertsPage() {
  const { user } = useAuth()
  return canInspectAccesses(user) ? <AdministrativeAlerts /> : <OperatorAlerts />
}
