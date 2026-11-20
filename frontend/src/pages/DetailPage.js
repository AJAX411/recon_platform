/** Ficha consultada por ID: descarta respuestas obsoletas, monta acciones autorizadas y relee tras guardar. */
import { button, dataGrid, el, link, loading, message, page } from '../components/dom.js'
import { resources, personName } from './resources.js'
import { mountDetailActions } from '../components/DetailActions.js'

export function mountDetail(ctx) {
  const { container, route, params, session, api } = ctx
  const spec = resources[route.resource]
  const view = page(route.title)
  const results = el('section', { className: 'detail-panel' })
  view.prepend(link(spec.root, '← Volver a ' + spec.title, { className: 'back-link' }))
  view.append(results); container.replaceChildren(view)
  let active = true
  let controller = null
  let actions = null
  let notice = ''
  async function load() {
    actions?.destroy(); actions = null
    controller?.abort()
    controller = new AbortController()
    const signal = controller.signal
    const epoch = session.getState().epoch
    results.replaceChildren(loading())
    try {
      const data = await api[spec.get](params.id, signal)
      if (!active || signal.aborted || epoch !== session.getState().epoch) return
      if (String(data?.[spec.id]) !== params.id) throw new Error('La respuesta no corresponde al registro solicitado.')
      results.replaceChildren(el('h2', {}, route.resource === 'people' ? personName(data) : data.nombre || data.login),
        dataGrid([['Referencia interna', data[spec.id]], ...spec.fields.map(([label, key]) => [label, data[key]])]))
      if (notice) results.prepend(message(notice, 'success'))
      actions = mountDetailActions(ctx, data, () => { notice = 'Operación confirmada. Se ha vuelto a consultar el registro.'; void load() })
      view.querySelector('.page-head').append(actions.actions)
      results.append(actions.node)
      if (route.resource === 'devices') results.append(message('Estado y modo administrativos; no confirman conexión ni operación física.', 'info'))
      if (route.resource === 'people') {
        results.append(message('Registro administrativo independiente de una cuenta web. ACTIVO no implica acceso autorizado.', 'info'))
      }
      results.append(el('p', { className: 'muted' }, 'La baja lógica conserva el registro y su historial; no elimina datos personales.'))
    } catch (error) {
      if (!active || signal.aborted || epoch !== session.getState().epoch) return
      results.replaceChildren(message(error.message), button('Reintentar consulta', load))
    }
  }
  void load()
  return () => { active = false; controller?.abort(); actions?.destroy(); view.remove() }
}
