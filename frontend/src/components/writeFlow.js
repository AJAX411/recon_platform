/** Coordinación de confirmación y escritura: bloqueo de doble envío, navegación y registro de resultados inciertos por identidad. */
import { confirmDialog } from './ConfirmDialog.js'
import { message } from './dom.js'

export function createWriteRegistry() {
  const uncertain = new Set()
  return { has: (key) => uncertain.has(key), add: (key) => uncertain.add(key), clear: () => uncertain.clear() }
}
export function createWriteFlow({ session, navigation, writeRegistry, invalidateReadings, key,
  feedback, lock = () => {}, isDirty = () => false, secret = false }) {
  const user = session.getState().user
  const owner = user.id_usuario + ':' + user.rol
  const registryKey = owner + ':' + key
  let phase = writeRegistry.has(registryKey) ? 'uncertain' : 'idle'
  let active = true
  let modal = null
  const describe = () => {
    if (phase === 'saved') return null
    if (phase === 'review') return { silent: true, allow: false }
    if (phase === 'sending') return { allow: false, message: 'Hay una escritura en curso. Espera su resultado antes de salir.' }
    if (phase === 'uncertain') return { message: 'No se confirmó la escritura. No la repitas; consulta el estado registrado. Salir no resuelve la incertidumbre.' }
    return isDirty() ? { message: 'Hay cambios sin guardar. ¿Deseas descartarlos?' } : null
  }
  const unregister = navigation.register(describe)
  function update(value) { phase = value; if (active) lock(['review', 'sending', 'uncertain'].includes(phase)) }
  if (phase === 'uncertain') {
    feedback.replaceChildren(message('Resultado incierto anterior en esta operación. No se habilita otro envío.', 'warning'))
    lock(true)
  }
  async function run(title, description, operation, onSaved, opener, { confirmLabel = 'Confirmar' } = {}) {
    if (phase !== 'idle') return false
    update('review')
    modal = confirmDialog(title, description, opener, confirmLabel)
    const accepted = await modal.promise
    modal = null
    if (!active || !accepted) { update('idle'); if (opener?.isConnected) opener.focus(); return false }
    update('sending')
    feedback.replaceChildren(message('Enviando operación…', 'info'))
    try {
      const data = await operation()
      invalidateReadings()
      update('saved')
      if (active && session.getState().user?.id_usuario === user.id_usuario && session.getState().user?.rol === user.rol) onSaved(data)
      return true
    } catch (error) {
      const uncertain = error.writeAttempted !== false
        && (!Number.isInteger(error.status) || error.status === 0 || error.status >= 500)
      if (uncertain) writeRegistry.add(registryKey)
      update(uncertain ? 'uncertain' : 'idle')
      if (active) feedback.replaceChildren(message(uncertain
        ? 'No se pudo confirmar si la operación quedó guardada. No se repetirá la solicitud; consulta el registro antes de actuar.'
        : secret ? 'No se pudo completar la operación de cuenta (HTTP ' + (error.status || 'sin respuesta') + ').'
          : error.message, uncertain ? 'warning' : 'danger'))
      return false
    }
  }
  return { run, getPhase: () => phase, saved: () => update('saved'),
    destroy: () => { active = false; unregister(); modal?.destroy() } }
}
