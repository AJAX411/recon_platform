import { useEffect, useRef, useState } from 'react'
import { searchEligiblePeople } from '../api/eventos.js'
import { useAuth } from '../auth/useAuth.js'
import { Alert, EmptyState, Skeleton } from '../components/Feedback.jsx'
import { Field, SelectField } from '../components/Field.jsx'

export function EligiblePersonSelector({ selected, onSelect, disabled = false, error }) {
  const { expire } = useAuth()
  const controllerRef = useRef(null)
  const [criterion, setCriterion] = useState('nombre')
  const [value, setValue] = useState('')
  const [people, setPeople] = useState([])
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('')

  useEffect(() => () => controllerRef.current?.abort(), [])

  function invalidate() {
    controllerRef.current?.abort()
    onSelect(null)
    setPeople([])
    setStatus('idle')
    setMessage('')
  }

  async function search(event) {
    event.preventDefault()
    const clean = value.trim()
    if (clean.length < 3 || clean.length > 50 || [...clean].some((char) => char.charCodeAt(0) < 32)) {
      setMessage('Escribe entre 3 y 50 caracteres válidos.')
      setStatus('error')
      return
    }
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    onSelect(null)
    setPeople([])
    setMessage('')
    setStatus('loading')
    try {
      const response = await searchEligiblePeople(criterion, clean, controller.signal)
      if (controller.signal.aborted) return
      setPeople(response.personas)
      setStatus('success')
    } catch (failure) {
      if (controller.signal.aborted) return
      if (failure.status === 401) expire()
      else { setMessage(failure.message); setStatus('error') }
    }
  }

  return <section className="form-panel access-selector" aria-labelledby="eligible-title">
    <h2 id="eligible-title">Persona elegible</h2>
    <p className="muted">Busca una Persona activa y selecciona el registro correcto. Se muestran hasta 20 coincidencias.</p>
    <form onSubmit={search} aria-label="Buscar Personas elegibles">
      <div className="form-grid">
        <SelectField id="persona_criterio" label="Buscar por" value={criterion} disabled={disabled}
          onChange={(event) => { setCriterion(event.target.value); invalidate() }}>
          <option value="nombre">Primer nombre o apellido</option>
          <option value="documento">Número de documento exacto</option>
          <option value="institucional">Identificador institucional exacto</option>
        </SelectField>
        <Field id="persona_valor" label="Valor de búsqueda" value={value} disabled={disabled}
          maxLength={50} onChange={(event) => { setValue(event.target.value); invalidate() }} />
      </div>
      <button className="btn btn-outline-secondary" type="submit" disabled={disabled || status === 'loading'}>
        Buscar Persona
      </button>
    </form>
    {status === 'loading' && <Skeleton rows={2} />}
    {status === 'error' && <Alert message={message} />}
    {status === 'success' && (people.length
      ? <SelectField id="persona_elegida" label="Seleccionar Persona" required error={error}
          value={selected?.id_persona || ''} disabled={disabled}
          onChange={(event) => onSelect(people.find((person) =>
            person.id_persona === Number(event.target.value)) || null)}>
          <option value="">Selecciona una Persona</option>
          {people.map((person) => <option key={person.id_persona} value={person.id_persona}>
            {person.nombre} · {person.tipo_documento} terminado en {person.documento_final} · ID {person.id_persona}
          </option>)}
        </SelectField>
      : <EmptyState>No hay Personas elegibles con esta búsqueda.</EmptyState>)}
    {status === 'success' && people.length === 20 &&
      <p className="muted mt-2">Si no encuentras a la Persona, refina la búsqueda con su documento o identificador exacto.</p>}
    {error && status !== 'success' && <Alert message={error} />}
  </section>
}
