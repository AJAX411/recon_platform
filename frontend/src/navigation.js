import { confirmDialog } from './components/ConfirmDialog.js'

export function createNavigation() {
  const blockers = new Set()
  let dialog = null
  function descriptions(reason) { return [...blockers].map((fn) => fn(reason)).filter(Boolean) }
  const unload = (event) => {
    if (descriptions('unload').length) { event.preventDefault(); event.returnValue = '' }
  }
  window.addEventListener('beforeunload', unload)
  function check(reason = 'navigate') {
    const blocks = descriptions(reason)
    if (!blocks.length) return true
    if (blocks.some((b) => b.silent)) return false
    if (dialog) return false
    const canLeave = blocks.every((b) => b.allow !== false)
    dialog = confirmDialog(canLeave ? '¿Salir de esta pantalla?' : 'Operación en curso',
      blocks.map((b) => b.message).join(' '), document.activeElement, canLeave ? 'Continuar y salir' : 'Entendido')
    return dialog.promise.then((accepted) => { dialog = null; return accepted && canLeave })
  }
  return { check, register: (fn) => { blockers.add(fn); return () => blockers.delete(fn) },
    destroy: () => { window.removeEventListener('beforeunload', unload); dialog?.destroy(); blockers.clear() } }
}
