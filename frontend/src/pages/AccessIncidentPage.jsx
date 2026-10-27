import { Link, useParams } from 'react-router-dom'
import { INCIDENCE_LABELS, formatBogota } from '../access/format.js'
import { getAccessIncident } from '../api/eventos.js'
import { DetailGrid } from '../components/DetailGrid.jsx'
import { Alert, Skeleton } from '../components/Feedback.jsx'
import { useResource } from '../hooks/useResource.js'

export function AccessIncidentPage() {
  const { id } = useParams()
  const { resource, status, error, retry } = useResource(getAccessIncident, id)

  return <section className="page-section" aria-labelledby="incident-title">
    <Link className="back-link" to="/eventos-acceso/alertas">← Volver a alertas</Link>
    <div className="page-head"><div><p className="eyebrow">Accesos manuales</p>
      <h1 id="incident-title">Detalle de incidencia</h1></div></div>
    {status === 'loading' && <Skeleton rows={5} />}
    {status === 'error' && <Alert message={error} onRetry={retry} />}
    {status === 'success' && resource && <section className="detail-panel" aria-labelledby="incident-data-title">
      <h2 id="incident-data-title">Evento {resource.id_evento_acceso}</h2>
      <DetailGrid items={[
        { label: 'Incidencia', value: INCIDENCE_LABELS[resource.tipo_incidencia_secuencia]
          || resource.tipo_incidencia_secuencia },
        { label: 'Movimiento', value: resource.tipo_movimiento },
        { label: 'Resultado', value: resource.resultado },
        { label: 'Método', value: resource.metodo_registro },
        { label: 'Fecha en Bogotá', value: formatBogota(resource.fecha_hora_ocurrencia) },
        { label: 'Persona', value: resource.nombre_persona },
        { label: 'ID de Persona', value: resource.id_persona },
        { label: 'Documento', value: resource.numero_documento
          ? `${resource.tipo_documento} · ${resource.numero_documento}` : null },
        { label: 'Punto de Acceso', value: resource.punto },
        { label: 'ID de Punto', value: resource.id_punto_acceso },
        { label: 'Usuario registrador', value: resource.usuario_registrador },
        { label: 'ID de usuario registrador', value: resource.id_usuario_registrador },
        { label: 'ID de dispositivo', value: resource.id_dispositivo },
      ]} />
    </section>}
  </section>
}
