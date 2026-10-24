import { Link } from 'react-router-dom'
import { listUsers } from '../api/usuarios.js'
import { usePagedList, PAGE_SIZE } from '../hooks/usePagedList.js'
import { Alert, EmptyState, Skeleton } from '../components/Feedback.jsx'
import { DataTable } from '../components/DataTable.jsx'
import { CollectionControls } from '../components/CollectionControls.jsx'
import { StatusBadge } from '../components/StatusBadge.jsx'

export function UsersListPage() {
  const page = usePagedList(listUsers, 'usuarios')
  return <section className="page-section" aria-labelledby="users-title">
    <div className="page-head"><div><p className="eyebrow">Identity/IAM</p><h1 id="users-title">Usuarios de plataforma</h1>
      <p className="page-intro">Cuentas web administradas por SUPERADMIN.</p></div>
      <Link className="btn btn-primary" to="/usuarios/nuevo">Crear cuenta</Link>
    </div>
    <div className="results-panel"><div className="results-heading"><h2>Resultados</h2>
      {page.status === 'success' && <span className="muted">Página {Math.floor(page.offset / PAGE_SIZE) + 1}</span>}</div>
      {page.status === 'loading' && <Skeleton rows={5} />}
      {page.status === 'error' && <Alert message={page.error} onRetry={page.retry} />}
      {page.status === 'success' && <>
        {page.rows.length ?
        <DataTable caption={`Usuarios de plataforma, página ${Math.floor(page.offset / PAGE_SIZE) + 1}`}
          columns={['Usuario', 'Rol', 'Estado', 'Acción']}>
          {page.rows.map((account) => <tr key={account.id_usuario}>
            <th scope="row">{account.login}<small>ID {account.id_usuario}</small></th>
            <td>{account.rol}</td><td><StatusBadge estado={account.estado} /></td>
            <td><Link to={`/usuarios/${account.id_usuario}`} aria-label={`Consultar cuenta ${account.login}`}>Consultar</Link></td>
          </tr>)}
        </DataTable>
        : <EmptyState>No hay cuentas en esta página.</EmptyState>}
        <CollectionControls label="usuarios" offset={page.offset} count={page.rows.length} previous={page.previous} next={page.next} />
      </>}
    </div>
  </section>
}
