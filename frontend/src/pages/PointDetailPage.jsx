import { useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { changePointState, editPoint, getPoint } from '../api/puntos.js'
import { canEditResources, useAuth } from '../auth/useAuth.js'
import { useResource } from '../hooks/useResource.js'
import { Alert, Skeleton } from '../components/Feedback.jsx'
import { DetailGrid } from '../components/DetailGrid.jsx'
import { Field } from '../components/Field.jsx'
import { StatusBadge } from '../components/StatusBadge.jsx'
import { Confirmation } from '../components/Confirmation.jsx'

export function PointDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const { user, expire } = useAuth()
  const { resource: point, setResource, status, error: loadError, retry } = useResource(getPoint, id)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [pendingEdit, setPendingEdit] = useState(null)
  const [pendingState, setPendingState] = useState(null)
  const editButtonRef = useRef(null)
  const stateButtonRef = useRef(null)

  async function update(operation, message) {
    setBusy(true)
    setError('')
    setNotice('')
    try { setResource(await operation()); setNotice(message) }
    catch (failure) {
      if (failure.status === 401) expire()
      else setError(failure.message)
    } finally { setBusy(false) }
  }

  function submitEdit(event) {
    event.preventDefault()
    if (busy || pendingEdit || pendingState) return
    const nombre = event.currentTarget.elements.namedItem('nombre').value.trim()
    const descripcion = event.currentTarget.elements.namedItem('descripcion').value.trim()
    if (!nombre) { setError('El nombre es obligatorio.'); event.currentTarget.elements.namedItem('nombre').focus(); return }
    if (nombre === point.nombre && (descripcion || null) === (point.descripcion || null)) return
    setPendingEdit({ nombre, descripcion })
  }

  const editSummary = pendingEdit ? [
    pendingEdit.nombre !== point.nombre && `Nombre: «${point.nombre}» → «${pendingEdit.nombre}».`,
    (pendingEdit.descripcion || null) !== (point.descripcion || null)
      && `Descripción: «${point.descripcion || 'Sin descripción'}» → «${pendingEdit.descripcion || 'Sin descripción'}».`,
  ].filter(Boolean).join(' ') : ''

  return <section className="page-section" aria-labelledby="point-title">
    <Link className="back-link" to="/puntos-acceso">← Volver a Puntos de Acceso</Link>
    {status === 'loading' && <Skeleton rows={6} />}
    {status === 'error' && <Alert message={loadError} onRetry={retry} />}
    {status === 'success' && point && <>
      <div className="page-head"><div><p className="eyebrow">Punto · ID {point.id_punto_acceso}</p>
        <h1 id="point-title">{point.nombre}</h1></div></div>
      {location.state?.created && <Alert message="Punto de Acceso creado correctamente." tone="success" />}
      <Alert message={notice} tone="success" /><Alert message={error} />
      <div className="detail-panel"><div className="detail-heading"><h2>Información administrativa</h2><StatusBadge estado={point.estado} /></div><DetailGrid items={[
        { label: 'Código', value: point.codigo }, { label: 'Nombre', value: point.nombre },
        { label: 'Descripción', value: point.descripcion },
        { label: 'Fecha de creación (UTC)', value: point.fecha_creacion },
        { label: 'Última actualización (UTC)', value: point.fecha_actualizacion },
      ]} /></div>
      {canEditResources(user) && <div className="form-panel mt-4"><h2>Editar punto</h2>
        <form key={`${point.nombre}:${point.descripcion}`} onSubmit={submitEdit} noValidate>
          <div className="form-grid"><Field id="nombre" label="Nombre" required maxLength={100} defaultValue={point.nombre} disabled={busy || Boolean(pendingEdit) || Boolean(pendingState)} />
            <Field id="descripcion" label="Descripción" maxLength={150} defaultValue={point.descripcion || ''} disabled={busy || Boolean(pendingEdit) || Boolean(pendingState)} /></div>
          <button ref={editButtonRef} className="btn btn-primary" type="submit" disabled={busy || Boolean(pendingEdit) || Boolean(pendingState)}>Guardar cambios</button>
        </form>
        {pendingEdit && <Confirmation
          title={`¿Guardar los cambios del punto ${point.codigo}?`}
          description={editSummary} confirmLabel="Confirmar edición" triggerRef={editButtonRef}
          onCancel={() => setPendingEdit(null)}
          onConfirm={() => update(() => editPoint(id, { nombre: pendingEdit.nombre, descripcion: pendingEdit.descripcion || null }), 'Punto de Acceso actualizado correctamente.')} />}
      </div>}
      <div className="form-panel mt-4"><h2>Estado del punto</h2>
        <button ref={stateButtonRef} className="btn btn-outline-secondary" type="button" disabled={busy || Boolean(pendingEdit) || Boolean(pendingState)}
          onClick={() => setPendingState(point.estado === 'ACTIVO' ? 'INACTIVO' : 'ACTIVO')}>
          {point.estado === 'ACTIVO' ? 'Desactivar punto' : 'Activar punto'}
        </button>
        {pendingState && <Confirmation
          title={`¿Cambiar el estado del punto ${point.codigo} a ${pendingState}?`}
          description="Este cambio modifica el estado administrativo del Punto de Acceso."
          confirmLabel="Confirmar cambio de estado" triggerRef={stateButtonRef}
          onCancel={() => setPendingState(null)}
          onConfirm={() => update(() => changePointState(id, pendingState), 'Estado actualizado correctamente.')} />}
      </div>
    </>}
  </section>
}
