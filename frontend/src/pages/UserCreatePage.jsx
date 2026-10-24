import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createUser, getRoles } from '../api/usuarios.js'
import { useAuth } from '../auth/useAuth.js'
import { Alert, EmptyState, Skeleton } from '../components/Feedback.jsx'
import { Field, SelectField } from '../components/Field.jsx'

const ASSIGNABLE = new Set(['ADMINISTRADOR', 'OPERADOR'])

export function UserCreatePage() {
  const { expire } = useAuth()
  const navigate = useNavigate()
  const [roles, setRoles] = useState([])
  const [status, setStatus] = useState('loading')
  const [reload, setReload] = useState(0)
  const [error, setError] = useState('')
  const [login, setLogin] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [rol, setRol] = useState('')
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let active = true
    getRoles().then((data) => {
      if (!active) return
      setRoles(data.roles.filter((item) => item.asignable && ASSIGNABLE.has(item.nombre)))
      setStatus('ready')
    }).catch((failure) => {
      if (!active) return
      if (failure.status === 401) expire()
      else { setError(failure.message); setStatus('error') }
    })
    return () => { active = false }
  }, [reload, expire])

  async function submit(event) {
    event.preventDefault()
    const next = {}
    if (!/^[a-z0-9][a-z0-9._-]{2,63}$/i.test(login.trim())) next.login = 'Usa entre 3 y 64 caracteres: letras, números, punto, guion o guion bajo.'
    if (contrasena.length < 12 || contrasena.length > 1024) next.contrasena = 'La contraseña debe tener entre 12 y 1024 caracteres.'
    if (!roles.some((item) => item.nombre === rol)) next.rol = 'Selecciona un rol asignable.'
    setErrors(next)
    if (Object.keys(next).length) { document.getElementById(Object.keys(next)[0])?.focus(); return }
    setSaving(true)
    setError('')
    try {
      const account = await createUser({ login: login.trim(), contrasena, rol })
      navigate(`/usuarios/${account.id_usuario}`, { replace: true, state: { created: true } })
    } catch (failure) {
      if (failure.status === 401) expire()
      else setError(failure.message)
    } finally { setContrasena(''); setSaving(false) }
  }

  return <section className="page-section" aria-labelledby="create-user-title">
    <Link className="back-link" to="/usuarios">← Volver a Usuarios</Link>
    <div className="page-head"><div><p className="eyebrow">Identity/IAM</p><h1 id="create-user-title">Crear cuenta</h1>
      <p className="page-intro">Las cuentas web son independientes de las Personas.</p></div></div>
    {status === 'loading' && <Skeleton rows={5} />}
    {status === 'error' && <Alert message={error} onRetry={() => setReload((value) => value + 1)} />}
    {status === 'ready' && (!roles.length ? <EmptyState>No hay roles asignables disponibles.</EmptyState> :
      <form className="form-panel" onSubmit={submit} noValidate>
        <Alert message={error} />
        <fieldset><legend>Datos de acceso</legend><div className="form-grid">
          <Field id="login" label="Usuario" required autoComplete="off" maxLength={64} value={login}
            onChange={(event) => { setLogin(event.target.value); setErrors({ ...errors, login: '' }) }} error={errors.login} />
          <SelectField id="rol" label="Rol" required value={rol}
            onChange={(event) => { setRol(event.target.value); setErrors({ ...errors, rol: '' }) }} error={errors.rol}>
            <option value="">Seleccionar rol</option>{roles.map((item) => <option key={item.nombre} value={item.nombre}>{item.nombre}</option>)}
          </SelectField>
          <Field id="contrasena" label="Contraseña inicial" type="password" required minLength={12} maxLength={1024}
            autoComplete="new-password" value={contrasena}
            onChange={(event) => { setContrasena(event.target.value); setErrors({ ...errors, contrasena: '' }) }} error={errors.contrasena} />
        </div></fieldset>
        <div className="form-actions"><button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Creando…' : 'Crear cuenta'}</button>
          <Link className="btn btn-outline-secondary" to="/usuarios">Cancelar</Link></div>
      </form>)}
  </section>
}
