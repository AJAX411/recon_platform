import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createPerson, getPersonTypes } from '../api/personas.js'
import { useAuth } from '../auth/useAuth.js'
import { Alert, Skeleton } from '../components/Feedback.jsx'
import { Field, SelectField } from '../components/Field.jsx'

const INITIAL = {
  primer_nombre: '', segundo_nombre: '', primer_apellido: '', segundo_apellido: '',
  tipo_persona: '', tipo_documento: '', numero_documento: '', identificador_institucional: '',
}
const REQUIRED = ['primer_nombre', 'primer_apellido', 'tipo_persona', 'tipo_documento', 'numero_documento']

function validate(values) {
  const errors = {}
  for (const key of REQUIRED) if (!values[key].trim()) errors[key] = 'Este campo es obligatorio.'
  if (values.tipo_persona === 'ESTUDIANTE' && !values.identificador_institucional.trim()) {
    errors.identificador_institucional = 'Obligatorio para ESTUDIANTE.'
  }
  return errors
}

export function PersonCreatePage() {
  const navigate = useNavigate()
  const { expire } = useAuth()
  const [values, setValues] = useState(INITIAL)
  const [errors, setErrors] = useState({})
  const [types, setTypes] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let active = true
    getPersonTypes().then((data) => {
      if (!active) return
      setTypes(data.tipos.filter((type) => type.estado === 'ACTIVO'))
      setStatus('ready')
    }).catch((failure) => {
      if (!active) return
      if (failure.status === 401) expire()
      else { setError(failure.message); setStatus('error') }
    })
    return () => { active = false }
  }, [reload, expire])

  function change(event) {
    const { name, value } = event.target
    setValues((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: '' }))
  }

  async function submit(event) {
    event.preventDefault()
    const nextErrors = validate(values)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) {
      document.getElementById(Object.keys(nextErrors)[0])?.focus()
      return
    }
    setSaving(true)
    setError('')
    const data = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value.trim()]))
    for (const key of ['segundo_nombre', 'segundo_apellido', 'identificador_institucional']) {
      if (!data[key]) data[key] = null
    }
    try {
      const created = await createPerson(data)
      navigate(`/personas/${created.id_persona}`, { replace: true, state: { created: true } })
    } catch (failure) {
      if (failure.status === 401) expire()
      else setError(failure.message)
    } finally { setSaving(false) }
  }

  return <section className="page-section" aria-labelledby="create-title">
    <Link className="back-link" to="/personas">← Volver a Personas</Link>
    <div className="page-head"><div><p className="eyebrow">Administración de Personas</p>
      <h1 id="create-title">Registrar Persona</h1>
      <p className="page-intro">Este registro contiene información administrativa. No realiza enrolamiento biométrico.</p></div></div>
    {status === 'loading' && <Skeleton rows={6} />}
    {status === 'error' && <Alert message={error} onRetry={() => setReload((number) => number + 1)} />}
    {status === 'ready' && <form className="form-panel" onSubmit={submit} noValidate>
      <Alert message={error} />
      <p className="required-note">Los campos con * son obligatorios.</p>
      <fieldset><legend>Identificación</legend><div className="form-grid">
        <Field id="primer_nombre" label="Primer nombre" required maxLength={100} value={values.primer_nombre} onChange={change} error={errors.primer_nombre} />
        <Field id="segundo_nombre" label="Segundo nombre" maxLength={100} value={values.segundo_nombre} onChange={change} error={errors.segundo_nombre} />
        <Field id="primer_apellido" label="Primer apellido" required maxLength={100} value={values.primer_apellido} onChange={change} error={errors.primer_apellido} />
        <Field id="segundo_apellido" label="Segundo apellido" maxLength={100} value={values.segundo_apellido} onChange={change} error={errors.segundo_apellido} />
      </div></fieldset>
      <fieldset><legend>Documento y categoría</legend><div className="form-grid">
        <SelectField id="tipo_persona" label="Tipo de Persona" required value={values.tipo_persona} onChange={change} error={errors.tipo_persona}>
          <option value="">Seleccionar tipo</option>{types.map((type) => <option key={type.id_tipo_persona} value={type.nombre}>{type.nombre}</option>)}
        </SelectField>
        <Field id="tipo_documento" label="Tipo de documento" required maxLength={20} value={values.tipo_documento} onChange={change} error={errors.tipo_documento} />
        <Field id="numero_documento" label="Número de documento" required maxLength={30} value={values.numero_documento} onChange={change} error={errors.numero_documento} />
        <Field id="identificador_institucional" label="Identificador institucional" maxLength={50}
          required={values.tipo_persona === 'ESTUDIANTE'} value={values.identificador_institucional} onChange={change} error={errors.identificador_institucional} />
      </div></fieldset>
      <div className="form-actions"><button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Guardando…' : 'Registrar Persona'}</button>
        <Link className="btn btn-outline-secondary" to="/personas">Cancelar</Link></div>
    </form>}
  </section>
}
