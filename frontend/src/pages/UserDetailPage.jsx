import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { changeUserRole, changeUserState, getRoles, getUser } from '../api/usuarios.js'
import { useAuth } from '../auth/useAuth.js'
import { useResource } from '../hooks/useResource.js'
import { Alert, Skeleton } from '../components/Feedback.jsx'
import { DetailGrid } from '../components/DetailGrid.jsx'
import { StatusBadge } from '../components/StatusBadge.jsx'
import { Confirmation } from '../components/Confirmation.jsx'

const ASSIGNABLE = new Set(['ADMINISTRADOR', 'OPERADOR'])

export function UserDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const { expire } = useAuth()
  const { resource: account, setResource, status, error: loadError, retry } = useResource(getUser, id)
  const accountId = account?.id_usuario
  const accountRole = account?.rol
  const [roles, setRoles] = useState([])
  const [rolesError, setRolesError] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [pendingRole, setPendingRole] = useState(null)
  const [pendingState, setPendingState] = useState(null)
  const roleButtonRef = useRef(null)
  const stateButtonRef = useRef(null)

  useEffect(() => {
    if (!accountId || accountRole === 'SUPERADMIN') return
    let active = true
    getRoles().then((data) => {
      if (active) { setRoles(data.roles.filter((item) => item.asignable && ASSIGNABLE.has(item.nombre))); setRolesError('') }
    }).catch((failure) => {
      if (!active) return
      if (failure.status === 401) expire()
      else setRolesError(failure.message)
    })
    return () => { active = false }
  }, [accountId, accountRole, expire])

  async function update(operation, successText) {
    setBusy(true)
    setError('')
    setNotice('')
    try { setResource(await operation()); setNotice(successText) }
    catch (failure) {
      if (failure.status === 401) expire()
      else setError(failure.message)
    } finally { setBusy(false) }
  }

  function submitRole(event) {
    event.preventDefault()
    if (busy || pendingRole || pendingState) return
    const rol = event.currentTarget.elements.namedItem('rol').value
    if (!roles.some((item) => item.nombre === rol)) { setError('Selecciona un rol asignable.'); return }
    if (rol !== account.rol) setPendingRole(rol)
  }

  return <section className="page-section" aria-labelledby="user-title">
    <Link className="back-link" to="/usuarios">← Volver a Usuarios</Link>
    {status === 'loading' && <Skeleton rows={5} />}
    {status === 'error' && <Alert message={loadError} onRetry={retry} />}
    {status === 'success' && account && <>
      <div className="page-head"><div><p className="eyebrow">Cuenta · ID {account.id_usuario}</p>
        <h1 id="user-title">{account.login}</h1></div></div>
      {location.state?.created && <Alert message="Cuenta creada correctamente." tone="success" />}
      <Alert message={notice} tone="success" /><Alert message={error} />
      <div className="detail-panel"><div className="detail-heading"><h2>Datos de la cuenta</h2><StatusBadge estado={account.estado} /></div><DetailGrid items={[
        { label: 'Identificador', value: account.id_usuario }, { label: 'Usuario', value: account.login },
        { label: 'Rol', value: account.rol },
      ]} /></div>
      {account.rol === 'SUPERADMIN' ? <div className="feature-panel"><p className="mb-0">La cuenta SUPERADMIN inicial está protegida. No se puede cambiar su rol ni su estado desde esta interfaz.</p></div> : <>
        <div className="form-panel mt-4"><h2>Rol</h2><Alert message={rolesError} />
          {roles.length > 0 && <form onSubmit={submitRole}>
            <label className="form-label" htmlFor="rol">Rol asignable</label>
            <select className="form-select mb-3" id="rol" name="rol" key={account.rol} defaultValue={account.rol} disabled={busy || Boolean(pendingRole) || Boolean(pendingState)}>
              {roles.map((item) => <option key={item.nombre} value={item.nombre}>{item.nombre}</option>)}
            </select>
            <button ref={roleButtonRef} className="btn btn-primary" type="submit" disabled={busy || Boolean(pendingRole) || Boolean(pendingState)}>Guardar rol</button>
          </form>}
          {pendingRole && <Confirmation
            title={`¿Cambiar el rol de la cuenta ${account.login}?`}
            description={`Rol actual: ${account.rol}. Rol propuesto: ${pendingRole}.`}
            confirmLabel="Confirmar cambio de rol" triggerRef={roleButtonRef}
            onCancel={() => setPendingRole(null)}
            onConfirm={() => update(() => changeUserRole(id, pendingRole), 'Rol actualizado correctamente.')} />}
        </div>
        <div className="form-panel mt-4"><h2>Estado de la cuenta</h2>
          <p className="muted">Desactivar una cuenta revoca sus sesiones vigentes.</p>
          <button ref={stateButtonRef} className="btn btn-outline-secondary" type="button" disabled={busy || Boolean(pendingRole) || Boolean(pendingState)}
            onClick={() => setPendingState(account.estado === 'ACTIVO' ? 'INACTIVO' : 'ACTIVO')}>
            {account.estado === 'ACTIVO' ? 'Desactivar cuenta' : 'Activar cuenta'}
          </button>
          {pendingState && <Confirmation
            title={`¿${pendingState === 'INACTIVO' ? 'Desactivar' : 'Activar'} la cuenta ${account.login}?`}
            description={pendingState === 'INACTIVO' ? 'La desactivación revoca las sesiones vigentes de esta cuenta.' : 'El estado administrativo de la cuenta cambiará a ACTIVO.'}
            confirmLabel="Confirmar cambio de estado" triggerRef={stateButtonRef}
            onCancel={() => setPendingState(null)}
            onConfirm={() => update(() => changeUserState(id, pendingState), 'Estado actualizado correctamente.')} />}
        </div>
      </>}
    </>}
  </section>
}
