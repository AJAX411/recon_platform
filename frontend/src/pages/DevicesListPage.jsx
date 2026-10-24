import { Link } from 'react-router-dom'
import { listDevices } from '../api/dispositivos.js'
import { canEditResources, useAuth } from '../auth/useAuth.js'
import { usePagedList, PAGE_SIZE } from '../hooks/usePagedList.js'
import { Alert, EmptyState, Skeleton } from '../components/Feedback.jsx'
import { DataTable } from '../components/DataTable.jsx'
import { CollectionControls } from '../components/CollectionControls.jsx'
import { Field, SelectField } from '../components/Field.jsx'
import { StatusBadge } from '../components/StatusBadge.jsx'

const FILTERS = { codigo: '', estado: '', modo_operacion: '', id_punto_acceso: '' }

export function DevicesListPage() {
  const { user } = useAuth()
  const page = usePagedList(listDevices, 'dispositivos', FILTERS)
  return <section className="page-section" aria-labelledby="devices-title">
    <div className="page-head"><div><p className="eyebrow">Integración Edge</p><h1 id="devices-title">Dispositivos Edge</h1>
      <p className="page-intro">Registros administrativos; el estado mostrado no confirma conexión física.</p></div>
      {canEditResources(user) && <Link className="btn btn-primary" to="/dispositivos-edge/nuevo">Registrar dispositivo</Link>}
    </div>
    <form className="filter-panel" onSubmit={page.apply} aria-label="Filtros de Dispositivos Edge">
      <fieldset><legend>Filtrar resultados</legend><div className="filter-grid">
        <Field id="codigo" label="Código" maxLength={20} value={page.draft.codigo}
          onChange={(event) => page.setDraft({ ...page.draft, codigo: event.target.value })} />
        <SelectField id="estado" label="Estado administrativo" value={page.draft.estado}
          onChange={(event) => page.setDraft({ ...page.draft, estado: event.target.value })}>
          <option value="">Todos</option><option value="ACTIVO">Activo</option><option value="INACTIVO">Inactivo</option>
        </SelectField>
        <SelectField id="modo_operacion" label="Modo de operación" value={page.draft.modo_operacion}
          onChange={(event) => page.setDraft({ ...page.draft, modo_operacion: event.target.value })}>
          <option value="">Todos</option><option value="ENTRADA">ENTRADA</option><option value="SALIDA">SALIDA</option><option value="AUTOMATICO">AUTOMATICO</option>
        </SelectField>
        <Field id="id_punto_acceso" label="ID del Punto de Acceso" type="number" min="1" step="1"
          value={page.draft.id_punto_acceso}
          onChange={(event) => page.setDraft({ ...page.draft, id_punto_acceso: event.target.value })} />
      </div><div className="filter-actions"><button className="btn btn-primary" type="submit">Aplicar filtros</button>
        <button className="btn btn-outline-secondary" type="button" onClick={page.clear}>Limpiar</button></div></fieldset>
    </form>
    <div className="results-panel"><div className="results-heading"><h2>Resultados</h2>
      {page.status === 'success' && <span className="muted">Página {Math.floor(page.offset / PAGE_SIZE) + 1}</span>}</div>
      {page.status === 'loading' && <Skeleton rows={5} />}
      {page.status === 'error' && <Alert message={page.error} onRetry={page.retry} />}
      {page.status === 'success' && <>
        {page.rows.length ?
        <DataTable caption={`Dispositivos Edge, página ${Math.floor(page.offset / PAGE_SIZE) + 1}`}
          columns={['Código', 'Nombre', 'Punto', 'Modo', 'Estado', 'Acción']}>
          {page.rows.map((device) => <tr key={device.id_dispositivo}>
            <th scope="row">{device.codigo}<small>ID {device.id_dispositivo}</small></th>
            <td>{device.nombre}</td><td>{device.id_punto_acceso}</td><td>{device.modo_operacion}</td>
            <td><StatusBadge estado={device.estado} /></td>
            <td><Link to={`/dispositivos-edge/${device.id_dispositivo}`} aria-label={`Consultar dispositivo ${device.codigo}`}>Consultar</Link></td>
          </tr>)}
        </DataTable>
        : <EmptyState>No se encontraron Dispositivos Edge con estos filtros.</EmptyState>}
        <CollectionControls label="Dispositivos Edge" offset={page.offset} count={page.rows.length} previous={page.previous} next={page.next} />
      </>}
    </div>
  </section>
}
