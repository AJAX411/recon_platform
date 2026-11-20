/** Consulta el detalle de incidencia administrativo y representa campos explícitos, sin exponerlo al OPERADOR. */
import { INCIDENCE_LABELS, formatBogota } from '../access/format.js'
import { button, dataGrid, el, link, loading, message, page } from '../components/dom.js'

export function mountIncident({ container, params, navigationState, session, api }) {
  const origin = ['/', '/eventos-acceso/historial', '/eventos-acceso/alertas', '/eventos-acceso/manual'].includes(navigationState.from)
    ? navigationState.from : '/eventos-acceso/alertas'
  const back = link(origin, '← Volver a ' + (origin === '/' ? 'Inicio' : origin.endsWith('historial') ? 'Historial' : origin.endsWith('manual') ? 'Registro manual' : 'Alertas'),
    { className: 'back-link' })
  const user = session.getState().user
  const owner = user.id_usuario + ':' + user.rol
  back.navigationState = { owner, accessContext: navigationState.owner === owner ? navigationState.accessContext : undefined }
  const view = page('Detalle de incidencia'), body = el('section', { className: 'detail-panel' })
  view.prepend(back); view.append(body); container.replaceChildren(view)
  let active = true, controller = null
  async function load() {
    controller?.abort(); controller = new AbortController()
    const signal = controller.signal, epoch = session.getState().epoch
    body.replaceChildren(loading())
    try {
      const data = await api.incident(params.id, signal)
      if (!active || signal.aborted || epoch !== session.getState().epoch) return
      if (String(data?.id_evento_acceso) !== params.id || !data.tipo_incidencia_secuencia) throw new Error('La respuesta no corresponde a la incidencia solicitada.')
      body.replaceChildren(dataGrid([
        ['Referencia interna', data.id_evento_acceso], ['Incidencia', INCIDENCE_LABELS[data.tipo_incidencia_secuencia] || data.tipo_incidencia_secuencia],
        ['Movimiento', data.tipo_movimiento], ['Resultado', data.resultado], ['Método', data.metodo_registro],
        ['Fecha y hora · Bogotá', formatBogota(data.fecha_hora_ocurrencia)], ['Persona', data.nombre_persona],
        ['ID de Persona', data.id_persona], ['Tipo de documento', data.tipo_documento], ['Número de documento', data.numero_documento],
        ['Punto', data.punto], ['ID de Punto', data.id_punto_acceso], ['Registrado por', data.usuario_registrador],
        ['ID de registrador', data.id_usuario_registrador], ['ID de dispositivo', data.id_dispositivo],
      ]))
    } catch (error) {
      if (!active || signal.aborted || epoch !== session.getState().epoch) return
      body.replaceChildren(message(error.message), button('Reintentar consulta', load))
    }
  }
  void load()
  return () => { active = false; controller?.abort(); view.remove() }
}
