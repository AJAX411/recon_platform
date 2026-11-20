/** Listados por recurso: filtros, paginación y columnas definidas; una consulta pendiente se cancela al desmontar. */
import { administrative } from '../auth/permissions.js'
import { button, el, link, loading, message, page } from '../components/dom.js'
import { filters as createFilters, pagination } from '../components/Filters.js'
import { detailAction, table } from '../components/Table.js'
import { resources } from './resources.js'

export function mountList({ container, route, session, api }) {
  const spec = resources[route.resource]
  const view = page(spec.title, route.resource === 'devices'
    ? 'Metadatos administrativos; el estado no confirma conexión ni funcionamiento físico.' : 'Consulta de registros administrativos.')
  if (administrative(session.getState().user)) view.firstChild.append(link(spec.newPath, spec.newLabel, { className: 'btn btn-outline-secondary' }))
  const results = el('section', { className: 'results-panel', 'aria-label': 'Resultados' })
  let values = Object.fromEntries(spec.filters.map((f) => [f.key, '']))
  let offset = 0
  let version = 0
  let controller = null
  let active = true
  let typeSelect = null
  let labels = new Map()
  let catalogController = null
  let savedRows = null
  const catalogNotice = el('div')
  if (spec.filters.length) {
    const filter = createFilters(spec.filters, values, (draft) => {
      if (draft.id_punto_acceso && !/^[1-9]\d{0,9}$/.test(draft.id_punto_acceso)) return 'El ID de Punto debe ser un entero positivo de hasta diez dígitos.'
      values = draft; offset = 0; void load(); return ''
    }, () => { values = Object.fromEntries(spec.filters.map((f) => [f.key, ''])); offset = 0; void load() })
    view.append(filter.node)
    typeSelect = filter.controls.get('tipo_persona')
  }
  view.append(catalogNotice, results); container.replaceChildren(view)
  function draw(rows) {
    results.replaceChildren(rows.length ? table(spec.title, spec.columns, rows.map((row) => {
      const cells = spec.cells(row)
      if (route.resource === 'people' && labels.has(row.tipo_documento)) {
        cells[1] = el('span', { title: labels.get(row.tipo_documento) }, row.tipo_documento)
      }
      return [...cells, Number.isSafeInteger(row[spec.id]) && row[spec.id] > 0
        ? detailAction('Ver detalles de ' + (row.nombre || row.login || row.primer_nombre || row.codigo || 'registro'),
          { href: spec.root + '/' + row[spec.id] }) : 'Detalle no disponible']
    })) : message('No hay registros en esta página.', 'info'),
    pagination(offset, rows.length, (next) => { offset = next; void load() }))
  }
  if (route.resource === 'people') {
    catalogController = new AbortController()
    const signal = catalogController.signal, epoch = session.getState().epoch
    Promise.all([api.personTypes(signal), api.documentTypes(signal)]).then(([types, documents]) => {
      if (!active || signal.aborted || epoch !== session.getState().epoch) return
      if (!Array.isArray(types?.tipos) || !Array.isArray(documents?.tipos_documento)) throw new Error('Catálogos no válidos.')
      typeSelect.replaceChildren(el('option', { value: '' }, 'Todos'),
        ...types.tipos.filter((type) => type.estado === 'ACTIVO').map((type) => el('option', { value: type.nombre }, type.nombre)))
      typeSelect.value = values.tipo_persona
      labels = new Map(documents.tipos_documento.map((type) => [type.codigo, type.nombre]))
      if (savedRows) draw(savedRows)
    }).catch((error) => {
      if (active && !signal.aborted && epoch === session.getState().epoch) {
        catalogNotice.replaceChildren(message('Catálogo no disponible; se conservan los códigos registrados. ' + error.message, 'warning'))
      }
    })
  }
  async function load() {
    controller?.abort()
    controller = new AbortController()
    const signal = controller.signal
    const revision = ++version
    const epoch = session.getState().epoch
    savedRows = null
    results.replaceChildren(loading())
    try {
      const data = await api[spec.list](values, offset, signal)
      if (!active || signal.aborted || revision !== version || epoch !== session.getState().epoch) return
      const rows = data?.[spec.collection]
      if (!Array.isArray(rows)) throw new Error('La respuesta no contiene un listado válido.')
      savedRows = rows
      draw(rows)
    } catch (error) {
      if (!active || signal.aborted || revision !== version || epoch !== session.getState().epoch) return
      results.replaceChildren(message(error.message), button('Reintentar consulta', load))
    }
  }
  void load()
  return () => { active = false; version += 1; controller?.abort(); catalogController?.abort(); view.remove() }
}
