/** Inicio renderizado desde el store de resumen; mantiene métricas administrativas y vista reducida de OPERADOR. */
import { administrative } from '../auth/permissions.js'
import { formatBogota } from '../access/format.js'
import { approximateTime } from '../access/projections.js'
import { movements } from '../access/Movements.js'
import { formatJornada } from '../dashboard/formatJornada.js'
import { button, el, loading, message, page } from '../components/dom.js'

export function mountDashboard({ container, dashboard, session }) {
  const view = page('Inicio', 'La jornada, de un vistazo.')
  const body = el('div')
  view.append(body); container.replaceChildren(view)
  let tableView = null
  function render(snapshot) {
    tableView?.destroy(); tableView = null
    body.replaceChildren()
    const { data, status, error } = snapshot
    if (status === 'loading' && !data) body.append(loading())
    if (error) body.append(message(error), button('Reintentar consulta', dashboard.refresh))
    if (!data) return
    const admin = administrative(session.getState().user)
    body.append(el('div', { className: 'dashboard-context' },
      el('strong', {}, 'Jornada ' + formatJornada(data.jornada)),
      el('p', { role: 'status', className: 'dashboard-meta' },
        (status === 'error' ? 'Datos desactualizados' : status === 'loading' ? 'Actualizando datos anteriores' : 'Última lectura')
        + ': ' + (admin ? formatBogota(data.generado_en) : approximateTime(data.generado_en) + ' (hora aproximada)'))))
    const rows = Array.isArray(data.ultimos_movimientos) ? data.ultimos_movimientos : null
    const metrics = admin
      ? [['Entradas de hoy', data.metricas?.entradas_hoy, 'Eventos autorizados'],
        ['Salidas de hoy', data.metricas?.salidas_hoy, 'Eventos autorizados'],
        ['Personas dentro (estimación)', data.metricas?.dentro_segun_registros, 'Según el historial registrado']]
      : [['Incidencias de hoy', data.incidencias_hoy, 'Conteo de la jornada · Bogotá'],
        ['Entradas mostradas', rows?.filter((r) => r.tipo_movimiento === 'ENTRADA').length, 'No es el total del día.'],
        ['Salidas mostradas', rows?.filter((r) => r.tipo_movimiento === 'SALIDA').length, 'No es el total del día.']]
    body.append(el('dl', { className: 'metric-grid' }, metrics.map(([label, value, hint]) =>
      el('div', { className: 'metric-card' }, el('dt', {}, label), el('dd', {},
        Number.isSafeInteger(value) && value >= 0 ? value : 'No disponible'), el('small', {}, hint)))))
    if (admin) body.append(el('p', { className: 'coverage-note' },
      'Sobre esta estimación. ' + (data.calidad_datos?.motivo || 'No certifica presencia física.'),
      data.calidad_datos?.personas_sin_historial > 0
        ? ' Personas sin historial autorizado: ' + data.calidad_datos.personas_sin_historial + '; presencia desconocida.' : ''))
    const results = el('section', { className: 'results-panel' }, el('h2', {}, 'Últimos movimientos'))
    if (!admin) results.append(el('p', {}, 'Jornada actual · sin identificación personal · hora aproximada.'))
    if (!rows) results.append(message('Movimientos no disponibles.', 'info'))
    else if (!rows.length) results.append(message('No hay movimientos disponibles para esta vista.', 'info'))
    else {
      tableView = movements(rows, { reduced: !admin })
      results.append(tableView.node)
    }
    body.append(results)
  }
  const unsubscribe = dashboard.subscribe(render)
  render(dashboard.getState())
  void dashboard.refresh()
  return () => { unsubscribe(); tableView?.destroy(); view.remove() }
}
