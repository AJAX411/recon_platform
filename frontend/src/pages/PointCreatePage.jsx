import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createPoint } from '../api/puntos.js'
import { useAuth } from '../auth/useAuth.js'
import { Alert } from '../components/Feedback.jsx'
import { Field } from '../components/Field.jsx'

export function PointCreatePage() {
  const { expire } = useAuth()
  const navigate = useNavigate()
  const [values, setValues] = useState({ codigo: '', nombre: '', descripcion: '' })
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
    if (!values.codigo.trim()) next.codigo = 'El código es obligatorio.'
    if (!values.nombre.trim()) next.nombre = 'El nombre es obligatorio.'
    setErrors(next)
    if (Object.keys(next).length) { document.getElementById(Object.keys(next)[0])?.focus(); return }
    setSaving(true)
    setError('')
    try {
      const created = await createPoint({ codigo: values.codigo.trim(), nombre: values.nombre.trim(),
        descripcion: values.descripcion.trim() || null })
      navigate(`/puntos-acceso/${created.id_punto_acceso}`, { replace: true, state: { created: true } })
    } catch (failure) {
      if (failure.status === 401) expire()
      else setError(failure.message)
    } finally { setSaving(false) }
  }

  return <section className="page-section" aria-labelledby="create-point-title">
    <Link className="back-link" to="/puntos-acceso">← Volver a Puntos de Acceso</Link>
    <div className="page-head"><div><p className="eyebrow">Accesos</p><h1 id="create-point-title">Crear Punto de Acceso</h1></div></div>
    <form className="form-panel" onSubmit={submit} noValidate><Alert message={error} />
      <fieldset><legend>Datos del punto</legend><div className="form-grid">
        <Field id="codigo" label="Código" required maxLength={20} value={values.codigo} onChange={change} error={errors.codigo} />
        <Field id="nombre" label="Nombre" required maxLength={100} value={values.nombre} onChange={change} error={errors.nombre} />
        <Field id="descripcion" label="Descripción" maxLength={150} value={values.descripcion} onChange={change} error={errors.descripcion} />
      </div></fieldset>
      <div className="form-actions"><button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Creando…' : 'Crear Punto de Acceso'}</button>
        <Link className="btn btn-outline-secondary" to="/puntos-acceso">Cancelar</Link></div>
    </form>
  </section>
}
