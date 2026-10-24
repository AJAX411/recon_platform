import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPersonTypes, listPeople } from '../api/personas.js'
import { useAuth } from '../auth/useAuth.js'
import { Alert, EmptyState, Skeleton } from '../components/Feedback.jsx'
import { Field, SelectField } from '../components/Field.jsx'
import { DataTable } from '../components/DataTable.jsx'
import { CollectionControls } from '../components/CollectionControls.jsx'
import { PAGE_SIZE } from '../hooks/usePagedList.js'

const INITIAL_FILTERS = { tipo_documento: '', numero_documento: '', identificador_institucional: '', tipo_persona: '', estado: '' }

function nameOf(person) {
  return [person.primer_nombre, person.segundo_nombre, person.primer_apellido, person.segundo_apellido].filter(Boolean).join(' ')
}

export function PeopleListPage() {
  const { expire } = useAuth()
  const [filters, setFilters] = useState(INITIAL_FILTERS)
  const [applied, setApplied] = useState(INITIAL_FILTERS)
  const [offset, setOffset] = useState(0)
  const [people, setPeople] = useState([])
  const [types, setTypes] = useState([])
  const [typesError, setTypesError] = useState('')
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let active = true
    getPersonTypes().then((data) => { if (active) { setTypes(data.tipos.filter((type) => type.estado === 'ACTIVO')); setTypesError('') } })
      .catch((failure) => {
        if (!active) return
        if (failure.status === 401) expire()
        else setTypesError(failure.message)
      })
    return () => { active = false }
  }, [reload, expire])

  useEffect(() => {
    const controller = new AbortController()
    setStatus('loading')
    setError('')
    listPeople(applied, offset, PAGE_SIZE, controller.signal)
      .then((data) => { setPeople(data.personas); setStatus('success') })
      .catch((failure) => {
        if (controller.signal.aborted) return
        if (failure.status === 401) expire()
        else { setError(failure.message); setStatus('error') }
      })
    return () => controller.abort()
  }, [applied, offset, reload, expire])

  function submitFilters(event) {
    event.preventDefault()
    const clean = Object.fromEntries(Object.entries(filters).map(([key, value]) => [key, value.trim()]))
    setOffset(0)
    setApplied(clean)
    setReload((number) => number + 1)
  }

  function clearFilters() {
    setFilters(INITIAL_FILTERS)
    setApplied(INITIAL_FILTERS)
    setOffset(0)
    setReload((number) => number + 1)
  }

  return <section className="page-section" aria-labelledby="people-title">
    <div className="page-head">
      <div><p className="eyebrow">Administración</p><h1 id="people-title">Personas</h1>
        <p className="page-intro">Registros administrativos de Personas.</p></div>
      <Link className="btn btn-primary" to="/personas/nueva">Registrar Persona</Link>
    </div>
    <form className="filter-panel" onSubmit={submitFilters} aria-label="Filtros de Personas">
      <Alert message={typesError} onRetry={() => setReload((number) => number + 1)} />
      <fieldset><legend>Filtrar resultados</legend>
        <div className="filter-grid">
          <Field id="numero_documento" label="Número de documento" maxLength={30} value={filters.numero_documento} onChange={(event) => setFilters({ ...filters, numero_documento: event.target.value })} />
          <Field id="tipo_documento" label="Tipo de documento" maxLength={20} value={filters.tipo_documento} onChange={(event) => setFilters({ ...filters, tipo_documento: event.target.value })} />
          <Field id="identificador_institucional" label="Identificador institucional" maxLength={50} value={filters.identificador_institucional} onChange={(event) => setFilters({ ...filters, identificador_institucional: event.target.value })} />
          <SelectField id="tipo_persona" label="Tipo de Persona" value={filters.tipo_persona} onChange={(event) => setFilters({ ...filters, tipo_persona: event.target.value })}>
            <option value="">Todos</option>{types.map((type) => <option key={type.id_tipo_persona} value={type.nombre}>{type.nombre}</option>)}
          </SelectField>
          <SelectField id="estado" label="Estado" value={filters.estado} onChange={(event) => setFilters({ ...filters, estado: event.target.value })}>
            <option value="">Todos</option><option value="ACTIVO">Activo</option><option value="INACTIVO">Inactivo</option>
          </SelectField>
        </div>
        <div className="filter-actions"><button className="btn btn-primary" type="submit">Aplicar filtros</button><button className="btn btn-outline-secondary" type="button" onClick={clearFilters}>Limpiar</button></div>
      </fieldset>
    </form>
    <div className="results-panel">
      <div className="results-heading"><h2>Resultados</h2>{status === 'success' && <span className="muted">Página {Math.floor(offset / PAGE_SIZE) + 1}</span>}</div>
      {status === 'loading' && <Skeleton rows={5} />}
      {status === 'error' && <Alert message={error} onRetry={() => setReload((number) => number + 1)} />}
      {status === 'success' && <>
        {people.length ?
        <DataTable caption={`Personas obtenidas de la API, página ${Math.floor(offset / PAGE_SIZE) + 1}`}
          columns={['Persona', 'Documento', 'Tipo', 'Estado', 'Acción']}>
          {people.map((person) => <tr key={person.id_persona}>
            <th scope="row">{nameOf(person)}<small>ID {person.id_persona}</small></th>
            <td>{person.tipo_documento} · {person.numero_documento}</td><td>{person.tipo_persona}</td>
            <td><span className={`status-pill ${person.estado === 'ACTIVO' ? 'active' : 'inactive'}`}>{person.estado}</span></td>
            <td><Link to={`/personas/${person.id_persona}`} aria-label={`Consultar ${nameOf(person)}`}>Consultar</Link></td>
          </tr>)}
        </DataTable>
        : <EmptyState>No se encontraron Personas con estos filtros.</EmptyState>}
        <CollectionControls label="Personas" offset={offset} count={people.length}
          previous={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))}
          next={() => setOffset((value) => Math.min(1_000_000, value + PAGE_SIZE))} />
      </>}
    </div>
  </section>
}
