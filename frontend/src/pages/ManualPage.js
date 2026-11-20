import { administrative } from '../auth/permissions.js'
import { INCIDENCE_LABELS, formatBogota } from '../access/format.js'
import { field } from '../components/Fields.js'
import { mountEligiblePersonSelector } from '../components/EligiblePersonSelector.js'
import { mountPointSelector } from '../components/PointSelector.js'
import { confirmDialog } from '../components/ConfirmDialog.js'
import { button, dataGrid, el, link, message, page } from '../components/dom.js'

export function mountManual({ container, api, session, manual, navigation }) {
  const view = page('Registrar entrada o salida', 'Declaración administrativa: no certifica presencia física ni acciona puertas.')
  const person = mountEligiblePersonSelector({ api })
  const point = mountPointSelector({ api, activeOnly: true, label: '2. Punto de Acceso ACTIVO' })
  const movement = field('tipo_movimiento_manual', '3. Movimiento declarado', { options: [
    { value: 'ENTRADA', label: 'ENTRADA' }, { value: 'SALIDA', label: 'SALIDA' },
  ] })
  const feedback = el('div', { tabIndex: -1 })
  const submit = el('button', { type: 'submit', className: 'btn btn-primary', 'aria-haspopup': 'dialog' }, 'Revisar declaración')
  const form = el('form', { className: 'form-panel manual-form', 'aria-label': 'Declarar movimiento manual', noValidate: true },
    person.node, point.node, el('fieldset', {}, el('legend', {}, '3. Movimiento'), movement.node), submit)
  const outcome = el('section', { className: 'detail-panel mt-4', tabIndex: -1, 'aria-live': 'polite' })
  const recovery = el('p', { className: 'muted' }, 'La clave solo existe en memoria. Si recargas tras un resultado incierto, solicita revisión antes de declarar de nuevo el mismo movimiento.')
  view.append(feedback, form, outcome, recovery); container.replaceChildren(view)
  let active = true, reviewing = false, dialog = null
  const dirty = () => Boolean(person.getSelected() || point.getSelected() || movement.input.value
    || document.getElementById('persona_valor')?.value || document.getElementById('codigo_punto')?.value)
  const unregister = navigation.register(() => reviewing ? { allow: false, silent: true }
    : !manual.getState() && dirty() ? { message: 'Hay una declaración sin confirmar. ¿Deseas descartar la selección?' } : null)
  form.addEventListener('submit', async (event) => {
    event.preventDefault()
    if (reviewing || manual.getState()) return
    const p = person.getSelected(), pointValue = point.getSelected(), type = movement.input.value
    if (!p || !pointValue || pointValue.estado !== 'ACTIVO' || !['ENTRADA', 'SALIDA'].includes(type)) {
      feedback.replaceChildren(message('Selecciona explícitamente una Persona elegible, un Punto ACTIVO y ENTRADA o SALIDA.'))
      feedback.focus(); return
    }
    feedback.replaceChildren()
    reviewing = true; submit.disabled = true
    const body = { id_persona: p.id_persona, id_punto_acceso: pointValue.id_punto_acceso, tipo_movimiento: type }
    dialog = confirmDialog('Confirmar movimiento manual', 'Declarar ' + type + ' de ' + p.nombre
      + ' en ' + pointValue.nombre + ' · ' + pointValue.codigo + '. El servidor validará nuevamente sus estados.', submit, 'Confirmar registro')
    const accepted = await dialog.promise; dialog = null
    reviewing = false; submit.disabled = false
    if (!active) return
    if (accepted) manual.start(body)
    else submit.focus()
  })
  function reset() {
    person.reset(); point.reset(); movement.input.value = ''; feedback.replaceChildren()
  }
  async function closeRequest() {
    dialog = confirmDialog('¿Cerrar esta solicitud?', 'Solo se cerrará la solicitud rechazada o no enviada. No confirma una operación incierta.', document.activeElement, 'Cerrar solicitud')
    const accepted = await dialog.promise; dialog = null
    if (active && accepted && manual.clear({ confirmed: true })) reset()
  }
  function render(state) {
    if (!active) return
    outcome.replaceChildren()
    if (!state) { if (!form.isConnected) view.insertBefore(form, outcome); return }
    // No arrastrar nombres de selección al resultado o a otra identidad.
    form.remove()
    if (state.phase === 'sending') outcome.append(el('h2', {}, 'Enviando declaración'), message('No cierres ni repitas la operación.', 'info'))
    else if (state.phase === 'success') {
      const data = state.response.data, admin = administrative(session.getState().user)
      outcome.append(el('h2', {}, state.response.status === 200 ? 'Declaración ya registrada' : 'Declaración registrada'),
        dataGrid([['Movimiento', data.tipo_movimiento], ['Resultado', data.resultado], ['Método', data.metodo_registro],
          [admin ? 'Instante en Bogotá' : 'Hora aproximada de Bogotá', admin ? formatBogota(data.fecha_hora_ocurrencia) : data.hora_local_aproximada],
          ...(admin ? [['Referencia interna', data.id_evento_acceso]] : [])]))
      if (data.tipo_incidencia_secuencia) {
        outcome.append(message('Incidencia de secuencia: ' + INCIDENCE_LABELS[data.tipo_incidencia_secuencia] + '. No equivale a denegación automática.', 'warning'))
        if (admin) {
          const detail = link('/eventos-acceso/incidencias/' + data.id_evento_acceso, 'Consultar incidencia', { className: 'btn btn-outline-secondary' })
          detail.navigationState = { from: '/eventos-acceso/manual', owner: session.getState().user.id_usuario + ':' + session.getState().user.rol }
          outcome.append(detail)
        }
      }
      outcome.append(button('Registrar otra declaración', () => { if (manual.clear()) reset() }))
    } else {
      outcome.append(el('h2', {}, 'No se confirmó el registro'), message(state.error, state.phase === 'uncertain' ? 'warning' : 'danger'))
      if (['preflight', 'uncertain'].includes(state.phase)) outcome.append(button('Reintentar la misma declaración', () => manual.retry()))
      if (['rejected', 'conflict', 'localError', 'preflight'].includes(state.phase)) outcome.append(button('Cerrar solicitud y revisar formulario', () => { void closeRequest() }))
    }
    outcome.focus()
  }
  const unsubscribe = manual.subscribe(render)
  render(manual.getState())
  return () => { active = false; dialog?.destroy(); unregister(); unsubscribe(); person.destroy(); point.destroy(); view.remove() }
}
