import { useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { changeDeviceMode, changeDeviceState, editDevice, getDevice } from '../api/dispositivos.js'
import { canEditResources, useAuth } from '../auth/useAuth.js'
import { useResource } from '../hooks/useResource.js'
import { Alert, Skeleton } from '../components/Feedback.jsx'
import { DetailGrid } from '../components/DetailGrid.jsx'
import { Field, SelectField } from '../components/Field.jsx'
import { StatusBadge } from '../components/StatusBadge.jsx'
import { Confirmation } from '../components/Confirmation.jsx'

export function DeviceDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const { user, expire } = useAuth()
  const { resource: device, setResource, status, error: loadError, retry } = useResource(getDevice, id)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [pendingName, setPendingName] = useState(null)
  const [pending, setPending] = useState(null)
  const nameButtonRef = useRef(null)
  const stateButtonRef = useRef(null)
  const modeButtonRef = useRef(null)

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

  function submitName(event) {
    event.preventDefault()
    if (busy || pending || pendingName) return
    const nombre = event.currentTarget.elements.namedItem('nombre').value.trim()
    if (!nombre) { setError('El nombre es obligatorio.'); event.currentTarget.elements.namedItem('nombre').focus(); return }
    if (nombre !== device.nombre) setPendingName(nombre)
  }

  function submitMode(event) {
    event.preventDefault()
    if (busy || pending || pendingName) return
    const modo = event.currentTarget.elements.namedItem('modo_operacion').value
    if (!['ENTRADA', 'SALIDA', 'AUTOMATICO'].includes(modo)) { setError('Selecciona un modo válido.'); return }
    if (modo !== device.modo_operacion) setPending({ kind: 'modo', value: modo })
  }

  return <section className="page-section" aria-labelledby="device-title">
    <Link className="back-link" to="/dispositivos-edge">← Volver a Dispositivos Edge</Link>
    {status === 'loading' && <Skeleton rows={6} />}
    {status === 'error' && <Alert message={loadError} onRetry={retry} />}
    {status === 'success' && device && <>
      <div className="page-head"><div><p className="eyebrow">Dispositivo · ID {device.id_dispositivo}</p>
        <h1 id="device-title">{device.nombre}</h1></div></div>
      {location.state?.created && <Alert message="Dispositivo registrado correctamente." tone="success" />}
      <Alert message={notice} tone="success" /><Alert message={error} />
      <p className="page-intro">El estado es administrativo y no indica conexión ni funcionamiento físico.</p>
      <div className="detail-panel"><div className="detail-heading"><h2>Información administrativa</h2><StatusBadge estado={device.estado} /></div><DetailGrid items={[
        { label: 'Código', value: device.codigo }, { label: 'Nombre', value: device.nombre },
        { label: 'Punto de Acceso', value: <Link to={`/puntos-acceso/${device.id_punto_acceso}`}>ID {device.id_punto_acceso}</Link> },
        { label: 'Modo de operación', value: device.modo_operacion },
        { label: 'Última comunicación registrada (UTC)', value: device.ultima_comunicacion },
        { label: 'Fecha de creación (UTC)', value: device.fecha_creacion },
        { label: 'Última actualización (UTC)', value: device.fecha_actualizacion },
      ]} /></div>
      {canEditResources(user) && <div className="form-panel mt-4"><h2>Editar nombre</h2>
        <form key={device.nombre} onSubmit={submitName} noValidate>
          <Field id="nombre" label="Nombre" required maxLength={100} defaultValue={device.nombre} disabled={busy || Boolean(pendingName) || Boolean(pending)} />
          <button ref={nameButtonRef} className="btn btn-primary" type="submit" disabled={busy || Boolean(pendingName) || Boolean(pending)}>Guardar nombre</button>
        </form>
        {pendingName && <Confirmation
          title={`¿Cambiar el nombre del dispositivo ${device.codigo}?`}
          description={`Nombre actual: «${device.nombre}». Nombre propuesto: «${pendingName}».`}
          confirmLabel="Confirmar edición" triggerRef={nameButtonRef}
          onCancel={() => setPendingName(null)}
          onConfirm={() => update(() => editDevice(id, pendingName), 'Nombre actualizado correctamente.')} />}
      </div>}
      <div className="form-panel mt-4"><h2>Estado administrativo</h2>
        <button ref={stateButtonRef} className="btn btn-outline-secondary" type="button" disabled={busy || Boolean(pendingName) || Boolean(pending)}
          onClick={() => setPending({ kind: 'estado', value: device.estado === 'ACTIVO' ? 'INACTIVO' : 'ACTIVO' })}>
          {device.estado === 'ACTIVO' ? 'Desactivar dispositivo' : 'Activar dispositivo'}
        </button>
        {pending?.kind === 'estado' && <Confirmation
          title={`¿Cambiar el estado del dispositivo ${device.codigo} a ${pending.value}?`}
          description="Esta acción modifica la configuración administrativa; no confirma conexión ni funcionamiento físico."
          confirmLabel="Confirmar cambio de estado" triggerRef={stateButtonRef}
          onCancel={() => setPending(null)}
          onConfirm={() => update(() => changeDeviceState(id, pending.value), 'Estado actualizado correctamente.')} />}
      </div>
      <div className="form-panel mt-4"><h2>Modo de operación</h2>
        <form onSubmit={submitMode}>
          <SelectField id="modo_operacion" label="Modo" key={device.modo_operacion} defaultValue={device.modo_operacion} disabled={busy || Boolean(pendingName) || Boolean(pending)}>
            <option value="ENTRADA">ENTRADA</option><option value="SALIDA">SALIDA</option><option value="AUTOMATICO">AUTOMATICO</option>
          </SelectField>
          <button ref={modeButtonRef} className="btn btn-primary device-mode-save" type="submit"
            disabled={busy || Boolean(pendingName) || Boolean(pending)} aria-describedby={pending?.kind === 'estado' ? 'device-pending-note' : undefined}>Guardar modo</button>
        </form>
        {pending?.kind === 'estado' && <p id="device-pending-note" className="muted mt-2 mb-0" role="status">Hay un cambio de estado pendiente de confirmación.</p>}
        {pending?.kind === 'modo' && <Confirmation
          title={`¿Cambiar el modo del dispositivo ${device.codigo} a ${pending.value}?`}
          description="Esta acción modifica la configuración administrativa; no confirma conexión ni funcionamiento físico."
          confirmLabel="Confirmar cambio de modo" triggerRef={modeButtonRef}
          onCancel={() => setPending(null)}
          onConfirm={() => update(() => changeDeviceMode(id, pending.value), 'Modo actualizado correctamente.')} />}
      </div>
    </>}
  </section>
}
