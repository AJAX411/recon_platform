import { listPoints } from '../api/puntos.js'
import { usePagedList, PAGE_SIZE } from '../hooks/usePagedList.js'
import { Alert, EmptyState, Skeleton } from '../components/Feedback.jsx'
import { CollectionControls } from '../components/CollectionControls.jsx'
import { DataTable } from '../components/DataTable.jsx'
import { Field } from '../components/Field.jsx'

const loadActivePoints = (filters, offset, limit, signal) =>
  listPoints({ estado: 'ACTIVO', codigo: filters.codigo }, offset, limit, signal)

export function ActivePointSelector({ selected, onSelect, disabled = false, error }) {
  const page = usePagedList(loadActivePoints, 'puntos', { codigo: '' })
  const active = page.rows.filter((point) => point.estado === 'ACTIVO')
  const unappliedCode = page.draft.codigo.trim() !== page.filters.codigo

  function apply(event) {
    onSelect(null)
    page.apply(event)
  }

  function clear() {
    onSelect(null)
    page.clear()
  }

  return <section className="form-panel access-selector" aria-labelledby="active-point-title">
    <h2 id="active-point-title">Punto de Acceso activo</h2>
    <p className="muted">Elige un Punto administrativo. Su estado se verificará otra vez al registrar.</p>
    <form onSubmit={apply} aria-label="Buscar Puntos de Acceso activos">
      <Field id="codigo_punto" label="Código exacto (opcional)" maxLength={20}
        value={page.draft.codigo} disabled={disabled}
        onChange={(event) => { onSelect(null); page.setDraft({ codigo: event.target.value }) }} />
      <div className="filter-actions">
        <button className="btn btn-primary" type="submit" disabled={disabled}>Aplicar filtro</button>
        <button className="btn btn-outline-secondary" type="button" disabled={disabled} onClick={clear}>Limpiar</button>
      </div>
    </form>
    {selected && <p className="access-selection" role="status">
      Seleccionado: {selected.codigo} · {selected.nombre}
    </p>}
    {unappliedCode && <p className="muted">Aplica el código antes de seleccionar un Punto de esta lista.</p>}
    {error && <Alert message={error} />}
    {page.status === 'loading' && <Skeleton rows={3} />}
    {page.status === 'error' && <Alert message={page.error} onRetry={page.retry} />}
    {page.status === 'success' && <>
      <p className="muted">Página {Math.floor(page.offset / PAGE_SIZE) + 1}</p>
      {active.length ? <DataTable caption="Puntos de Acceso activos disponibles"
        columns={['Código', 'Nombre', 'Selección']}>
        {active.map((point) => <tr key={point.id_punto_acceso}>
          <th scope="row">{point.codigo}</th><td>{point.nombre}</td>
          <td><button type="button" className="btn btn-outline-secondary btn-sm"
            disabled={disabled || unappliedCode || selected?.id_punto_acceso === point.id_punto_acceso}
            onClick={() => onSelect(point)}>
            {selected?.id_punto_acceso === point.id_punto_acceso ? 'Seleccionado' : 'Seleccionar'}
          </button></td>
        </tr>)}
      </DataTable> : <EmptyState>No hay Puntos activos en esta página.</EmptyState>}
      <CollectionControls label="Puntos activos" offset={page.offset} count={page.rows.length}
        previous={page.previous} next={page.next} />
    </>}
  </section>
}
