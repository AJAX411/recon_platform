import { Link } from 'react-router-dom'
import { listPoints } from '../api/puntos.js'
import { canEditResources, useAuth } from '../auth/useAuth.js'
import { usePagedList, PAGE_SIZE } from '../hooks/usePagedList.js'
import { Alert, EmptyState, Skeleton } from '../components/Feedback.jsx'
import { DataTable } from '../components/DataTable.jsx'
import { CollectionControls } from '../components/CollectionControls.jsx'
import { Field, SelectField } from '../components/Field.jsx'
import { StatusBadge } from '../components/StatusBadge.jsx'

const FILTERS = { codigo: '', estado: '' }

export function PointsListPage() {
  const { user } = useAuth()
  const page = usePagedList(listPoints, 'puntos', FILTERS)
  return <section className="page-section" aria-labelledby="points-title">
    <div className="page-head"><div><p className="eyebrow">Accesos</p><h1 id="points-title">Puntos de Acceso</h1>
      <p className="page-intro">Ubicaciones administrativas registradas en la plataforma.</p></div>
      {canEditResources(user) && <Link className="btn btn-primary" to="/puntos-acceso/nuevo">Crear Punto de Acceso</Link>}
    </div>
    <form className="filter-panel" onSubmit={page.apply} aria-label="Filtros de Puntos de Acceso">
      <fieldset><legend>Filtrar resultados</legend><div className="filter-grid">
        <Field id="codigo" label="Código" maxLength={20} value={page.draft.codigo}
          onChange={(event) => page.setDraft({ ...page.draft, codigo: event.target.value })} />
        <SelectField id="estado" label="Estado" value={page.draft.estado}
          onChange={(event) => page.setDraft({ ...page.draft, estado: event.target.value })}>
          <option value="">Todos</option><option value="ACTIVO">Activo</option><option value="INACTIVO">Inactivo</option>
        </SelectField>
      </div><div className="filter-actions"><button className="btn btn-primary" type="submit">Aplicar filtros</button>
        <button className="btn btn-outline-secondary" type="button" onClick={page.clear}>Limpiar</button></div></fieldset>
    </form>
    <div className="results-panel"><div className="results-heading"><h2>Resultados</h2>
      {page.status === 'success' && <span className="muted">Página {Math.floor(page.offset / PAGE_SIZE) + 1}</span>}</div>
      {page.status === 'loading' && <Skeleton rows={5} />}
      {page.status === 'error' && <Alert message={page.error} onRetry={page.retry} />}
      {page.status === 'success' && <>
        {page.rows.length ?
        <DataTable caption={`Puntos de Acceso, página ${Math.floor(page.offset / PAGE_SIZE) + 1}`}
          columns={['Código', 'Nombre', 'Estado', 'Acción']}>
          {page.rows.map((point) => <tr key={point.id_punto_acceso}>
            <th scope="row">{point.codigo}<small>ID {point.id_punto_acceso}</small></th>
            <td>{point.nombre}</td><td><StatusBadge estado={point.estado} /></td>
            <td><Link to={`/puntos-acceso/${point.id_punto_acceso}`} aria-label={`Consultar punto ${point.codigo}`}>Consultar</Link></td>
          </tr>)}
        </DataTable>
        : <EmptyState>No se encontraron Puntos de Acceso con estos filtros.</EmptyState>}
        <CollectionControls label="Puntos de Acceso" offset={page.offset} count={page.rows.length} previous={page.previous} next={page.next} />
      </>}
    </div>
  </section>
}
