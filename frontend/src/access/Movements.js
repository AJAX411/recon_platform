/** Tabla de movimientos y detalle accesible; selecciona proyección administrativa o reducida sin inventar datos. */
import { INCIDENCE_LABELS, formatBogota } from './format.js'
import { approximateTime, checkReduced } from './projections.js'
import { dataGrid, el, link } from '../components/dom.js'
import { detailAction, table } from '../components/Table.js'
import { openDialog } from '../components/Dialog.js'

export function movements(rows, { reduced, directIncident = false, origin = '/', accessContext, owner } = {}) {
  let close = () => {}
  if (reduced) return { node: table('Movimientos de la jornada · hora aproximada de Bogotá',
    ['Movimiento', 'Resultado', 'Hora aproximada de Bogotá'],
    checkReduced(rows).map((row) => [row.tipo_movimiento, row.resultado, approximateTime(row.hora_local_aproximada)])),
    destroy: () => {} }
  const fields = [
    ['Fecha y hora · Bogotá', 'fecha_hora_ocurrencia', formatBogota],
    ['Persona', 'nombre_persona'], ['Punto de Acceso', 'punto'], ['Movimiento', 'tipo_movimiento'],
    ['Resultado', 'resultado'], ['Incidencia', 'tipo_incidencia_secuencia', (v) => INCIDENCE_LABELS[v] || v],
    ['Registrado por', 'usuario_registrador'], ['Referencia interna', 'id_evento_acceso'],
  ]
  const state = { from: origin, accessContext, owner }
  const node = table(directIncident ? 'Incidencias consultables' : 'Movimientos consultables',
    ['Fecha y hora · Bogotá', 'Persona', 'Punto', 'Movimiento', 'Resultado', 'Detalle'],
    rows.map((row) => {
      const incident = row.tipo_incidencia_secuencia && Number.isSafeInteger(row.id_evento_acceso) && row.id_evento_acceso > 0
      const href = '/eventos-acceso/incidencias/' + row.id_evento_acceso
      let action
      if (directIncident) action = incident ? detailAction('Ver detalles de incidencia ' + row.id_evento_acceso, { href, state }) : 'Incidencia no disponible'
      else action = detailAction('Ver detalles del movimiento ' + row.id_evento_acceso, { onClick: (event) => {
        close()
        const content = el('div', {}, dataGrid(fields.filter(([, key]) => row[key] !== null && row[key] !== undefined && row[key] !== '')
          .map(([label, key, format]) => [label, format ? format(row[key]) : row[key]])))
        if (incident) {
          const target = link(href, 'Consultar ficha de incidencia', { className: 'btn btn-outline-secondary mt-3' })
          target.navigationState = state
          target.addEventListener('click', () => close())
          content.append(target)
        }
        close = openDialog('Detalles del movimiento', content, event.currentTarget)
      } })
      return [formatBogota(row.fecha_hora_ocurrencia), row.nombre_persona || 'Sin Persona identificada',
        row.punto, row.tipo_movimiento, row.resultado, action]
    }))
  return { node, destroy: () => close() }
}
