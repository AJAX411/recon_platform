import { useState } from 'react'
import { Alert } from '../components/Feedback.jsx'
import { Field, SelectField } from '../components/Field.jsx'
import { INCIDENCE_LABELS, validateAdminFilters } from './format.js'

export function AccessAdminFilters({ page, label }) {
  const [validation, setValidation] = useState('')
  const draft = page.draft

  function change(name, value) {
    page.setDraft({ ...draft, [name]: value })
    setValidation('')
  }

  function apply(event) {
    event.preventDefault()
    const failure = validateAdminFilters(draft)
    if (failure) { setValidation(failure); return }
    setValidation('')
    page.apply(event)
  }

  function clear() {
    setValidation('')
    page.clear()
  }

  return <form className="filter-panel" onSubmit={apply} aria-label={`Filtros de ${label}`}>
    <fieldset><legend>Filtrar resultados</legend>
      <Alert message={validation} />
      <div className="filter-grid">
        <Field id="id_persona_filtro" label="ID de Persona" type="number" min="1" step="1"
          value={draft.id_persona} onChange={(event) => change('id_persona', event.target.value)} />
        <Field id="id_punto_filtro" label="ID de Punto" type="number" min="1" step="1"
          value={draft.id_punto_acceso} onChange={(event) => change('id_punto_acceso', event.target.value)} />
        <SelectField id="movimiento_filtro" label="Movimiento" value={draft.tipo_movimiento}
          onChange={(event) => change('tipo_movimiento', event.target.value)}>
          <option value="">Todos</option><option value="ENTRADA">ENTRADA</option>
          <option value="SALIDA">SALIDA</option>
        </SelectField>
        <SelectField id="resultado_filtro" label="Resultado" value={draft.resultado}
          onChange={(event) => change('resultado', event.target.value)}>
          <option value="">Todos</option><option value="AUTORIZADO">AUTORIZADO</option>
          <option value="RECHAZADO">RECHAZADO</option>
        </SelectField>
        <SelectField id="incidencia_filtro" label="Incidencia" value={draft.tipo_incidencia_secuencia}
          onChange={(event) => change('tipo_incidencia_secuencia', event.target.value)}>
          <option value="">Todas</option>
          {Object.entries(INCIDENCE_LABELS).map(([code, name]) =>
            <option key={code} value={code}>{name}</option>)}
        </SelectField>
        <Field id="desde_filtro" label="Desde (día Bogotá)" type="date" value={draft.desde}
          onChange={(event) => change('desde', event.target.value)} />
        <Field id="hasta_filtro" label="Hasta (día incluido, Bogotá)" type="date" value={draft.hasta}
          onChange={(event) => change('hasta', event.target.value)} />
      </div>
      <p className="muted">Se consultan días civiles completos de America/Bogota; el día final está incluido.</p>
      <div className="filter-actions">
        <button className="btn btn-primary" type="submit">Aplicar filtros</button>
        <button className="btn btn-outline-secondary" type="button" onClick={clear}>Limpiar</button>
      </div>
    </fieldset>
  </form>
}
