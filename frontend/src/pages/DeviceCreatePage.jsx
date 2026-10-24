import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createDevice } from '../api/dispositivos.js'
import { useAuth } from '../auth/useAuth.js'
import { Alert } from '../components/Feedback.jsx'
import { Field, SelectField } from '../components/Field.jsx'

export function DeviceCreatePage() {
  const { expire } = useAuth()
  const navigate = useNavigate()
  const [values, setValues] = useState({ id_punto_acceso: '', codigo: '', nombre: '', modo_operacion: '' })
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  function change(event) {
    const { name, value } = event.target
    setValues((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: '' }))
  }

  async function submit(event) {
    event.preventDefault()
    const next = {}
    const pointId = Number(values.id_punto_acceso)
    if (!Number.isSafeInteger(pointId) || pointId <= 0 || !values.id_punto_acceso.trim()) next.id_punto_acceso = 'Indica el ID entero positivo de un Punto de Acceso.'
    if (!values.codigo.trim()) next.codigo = 'El código es obligatorio.'
    if (!values.nombre.trim()) next.nombre = 'El nombre es obligatorio.'
    if (!['ENTRADA', 'SALIDA', 'AUTOMATICO'].includes(values.modo_operacion)) next.modo_operacion = 'Selecciona un modo válido.'
    setErrors(next)
    if (Object.keys(next).length) { document.getElementById(Object.keys(next)[0])?.focus(); return }
    setSaving(true)
    setError('')
    try {
      const created = await createDevice({ id_punto_acceso: pointId, codigo: values.codigo.trim(),
        nombre: values.nombre.trim(), modo_operacion: values.modo_operacion })
      navigate(`/dispositivos-edge/${created.id_dispositivo}`, { replace: true, state: { created: true } })
    } catch (failure) {
      if (failure.status === 401) expire()
      else setError(failure.message)
    } finally { setSaving(false) }
  }

  return <section className="page-section" aria-labelledby="create-device-title">
    <Link className="back-link" to="/dispositivos-edge">← Volver a Dispositivos Edge</Link>
    <div className="page-head"><div><p className="eyebrow">Integración Edge</p><h1 id="create-device-title">Registrar dispositivo</h1>
      <p className="page-intro">Registro administrativo. No establece conexión con Raspberry Pi ni activa el dispositivo.</p></div></div>
    <form className="form-panel" onSubmit={submit} noValidate><Alert message={error} />
      <fieldset><legend>Datos del dispositivo</legend><div className="form-grid">
        <Field id="id_punto_acceso" label="ID del Punto de Acceso" type="number" required min="1" step="1"
          value={values.id_punto_acceso} onChange={change} error={errors.id_punto_acceso} />
        <Field id="codigo" label="Código" required maxLength={20} value={values.codigo} onChange={change} error={errors.codigo} />
        <Field id="nombre" label="Nombre" required maxLength={100} value={values.nombre} onChange={change} error={errors.nombre} />
        <SelectField id="modo_operacion" label="Modo de operación" required value={values.modo_operacion} onChange={change} error={errors.modo_operacion}>
          <option value="">Seleccionar modo</option><option value="ENTRADA">ENTRADA</option><option value="SALIDA">SALIDA</option><option value="AUTOMATICO">AUTOMATICO</option>
        </SelectField>
      </div></fieldset>
      <p className="muted">El ID debe corresponder a un <Link to="/puntos-acceso">Punto de Acceso existente</Link>. El backend comprueba la asociación.</p>
      <div className="form-actions"><button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Registrando…' : 'Registrar dispositivo'}</button>
        <Link className="btn btn-outline-secondary" to="/dispositivos-edge">Cancelar</Link></div>
    </form>
  </section>
}
