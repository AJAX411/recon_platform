/** Historial e incidencias por rol; limita filtros de OPERADOR y conserva la selección administrativa en la URL. */
import { administrative } from '../auth/permissions.js'
import { ADMIN_FILTERS, INCIDENCE_LABELS, validateAdminFilters } from '../access/format.js'
import { movements } from '../access/Movements.js'
import { button, el, loading, message, page } from '../components/dom.js'
import { filters as createFilters, pagination } from '../components/Filters.js'

export function mountEvents({ container, route, navigationState, session, api }) {
  const admin = administrative(session.getState().user)
  const alerts = route.page === 'alerts'
  const initial = admin ? ADMIN_FILTERS : {}
  const user = session.getState().user
  const owner = user.id_usuario + ':' + user.rol
  // El contexto de filtros tampoco se restaura desde otra cuenta/rol.
  const saved = navigationState.owner === owner ? navigationState.accessContext : null
  let values = Object.fromEntries(Object.entries(initial).map(([key, value]) => [
    key, typeof saved?.filters?.[key] === 'string' ? saved.filters[key] : value,
  ]))
  let offset = admin && Number.isInteger(saved?.offset) && saved.offset >= 0 && saved.offset <= 1_000_000 ? saved.offset : 0
  const view = page(admin ? route.title : alerts ? 'Alertas de la jornada' : 'Historial de la jornada',
    admin ? 'Consulta administrativa autorizada · fechas de Bogotá.'
      : alerts ? 'Conteos agregados del día actual en Bogotá, sin datos personales.' : 'Movimiento, resultado y hora aproximada de la jornada Bogotá.')
  const results = el('section', { className: 'results-panel', 'aria-label': 'Resultados' })
  let active = true, controller = null, tableView = null
  let version = 0
  const context = () => ({ filters: { ...values }, offset })
  function remember() {
    if (admin) {
      history.replaceState({ ...history.state, owner, accessContext: context() }, '', location.href)
      window.dispatchEvent(new Event('recon:context'))
    }
  }
  if (admin) {
    const specs = [
      { key: 'id_persona', label: 'ID de Persona', max: 10 }, { key: 'id_punto_acceso', label: 'ID de Punto', max: 10 },
      { key: 'tipo_movimiento', label: 'Movimiento', options: ['ENTRADA', 'SALIDA'] },
      { key: 'resultado', label: 'Resultado', options: ['AUTORIZADO', 'RECHAZADO'] },
      { key: 'tipo_incidencia_secuencia', label: 'Incidencia', options: Object.keys(INCIDENCE_LABELS) },
      { key: 'desde', label: 'Desde (día Bogotá)', type: 'date' },
      { key: 'hasta', label: 'Hasta (día incluido, Bogotá)', type: 'date' },
    ]
    view.append(createFilters(specs, values, (draft) => {
      const error = validateAdminFilters(draft)
      if (error) return error
      values = draft; offset = 0; remember(); void load(); return ''
    }, () => { values = { ...initial }; offset = 0; remember(); void load() }).node)
  }
  view.append(results); container.replaceChildren(view)
  async function load() {
    controller?.abort(); tableView?.destroy(); tableView = null
    controller = new AbortController()
    const signal = controller.signal, revision = ++version, epoch = session.getState().epoch
    results.replaceChildren(loading())
    try {
      const data = !admin && alerts ? await api.alertCounts(signal)
        : await api[alerts ? 'alerts' : 'history'](values, offset, signal)
      if (!active || signal.aborted || revision !== version || epoch !== session.getState().epoch) return
      if (!admin && alerts) {
        const counts = data?.conteos_por_incidencia
        if (!counts || typeof counts !== 'object' || Array.isArray(counts)) throw new Error('No se recibieron conteos válidos.')
        if (Object.keys(counts).some((key) => !(key in INCIDENCE_LABELS))) throw new Error('La respuesta contiene categorías de incidencia no reconocidas.')
        // Solo categorías de incidencia conocidas; ningún campo extra se presenta.
        const entries = Object.entries(counts).filter(([key]) => key in INCIDENCE_LABELS)
        if (entries.some(([, count]) => !Number.isSafeInteger(count) || count < 0)) throw new Error('No se recibieron conteos válidos.')
        results.replaceChildren(entries.length ? el('dl', { className: 'access-counts' }, entries.map(([type, count]) =>
          el('div', {}, el('dt', {}, INCIDENCE_LABELS[type]), el('dd', {}, count))))
          : message('No hay incidencias en la jornada actual.', 'info'))
        return
      }
      const actualRows = data?.[alerts ? 'alertas' : 'eventos']
      if (!Array.isArray(actualRows)) throw new Error('La respuesta no contiene un listado válido.')
      if (actualRows.length) {
        tableView = movements(actualRows, { reduced: !admin, directIncident: alerts,
          origin: route.path, accessContext: context(), owner })
        results.replaceChildren(tableView.node)
      } else results.replaceChildren(message('No hay movimientos en esta página.', 'info'))
      results.append(pagination(offset, actualRows.length, (next) => { offset = next; remember(); void load() }))
    } catch (error) {
      if (!active || signal.aborted || revision !== version || epoch !== session.getState().epoch) return
      results.replaceChildren(message(error.message), button('Reintentar consulta', load))
    }
  }
  void load()
  return () => { active = false; version += 1; controller?.abort(); tableView?.destroy(); view.remove() }
}
