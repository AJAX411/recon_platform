import { Link } from 'react-router-dom'
import { DataTable } from '../components/DataTable.jsx'
import { INCIDENCE_LABELS, formatBogota } from './format.js'

export function AccessEventsTable({ rows, reduced, caption }) {
  if (reduced) return <DataTable caption={caption} columns={['Movimiento', 'Resultado', 'Hora aproximada de Bogotá']}>
    {rows.map((row, index) => <tr key={index}>
      <th scope="row">{row.tipo_movimiento}</th>
      <td>{row.resultado}</td>
      <td>{formatBogota(row.hora_local_aproximada)}</td>
    </tr>)}
  </DataTable>

  return <DataTable caption={caption}
    columns={['Evento', 'Fecha en Bogotá', 'Persona', 'Punto', 'Movimiento', 'Resultado', 'Incidencia', 'Actor', 'Detalle']}>
    {rows.map((row) => <tr key={row.id_evento_acceso}>
      <th scope="row">ID {row.id_evento_acceso}</th>
      <td>{formatBogota(row.fecha_hora_ocurrencia)}</td>
      <td>{row.nombre_persona || 'Sin Persona identificada'}</td>
      <td>{row.punto}</td>
      <td>{row.tipo_movimiento}</td>
      <td>{row.resultado}</td>
      <td>{INCIDENCE_LABELS[row.tipo_incidencia_secuencia] || 'Sin incidencia'}</td>
      <td>{row.usuario_registrador || 'No registrado'}</td>
      <td>{row.tipo_incidencia_secuencia
        ? <Link to={`/eventos-acceso/incidencias/${row.id_evento_acceso}`}>Consultar incidencia</Link>
        : '—'}</td>
    </tr>)}
  </DataTable>
}
