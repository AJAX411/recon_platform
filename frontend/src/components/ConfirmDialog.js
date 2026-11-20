import { button, el } from './dom.js'
import { openDialog } from './Dialog.js'
let confirmationSequence = 0

export function confirmDialog(title, description, opener = document.activeElement, confirmLabel = 'Confirmar') {
  let destroy = () => {}
  let finished = false
  let settle
  const promise = new Promise((resolve) => { settle = resolve })
  const finish = (accepted) => {
    if (finished) return
    finished = true
    destroy()
    settle(accepted)
  }
  // Los ID de DOM no requieren UUID; su indisponibilidad no debe romper la UI.
  const info = el('div', { id: 'confirmation-description-' + (++confirmationSequence) }, description)
  const cancel = button('Cancelar', () => finish(false))
  const confirm = button(confirmLabel, () => finish(true), { className: 'btn btn-primary' })
  destroy = openDialog(title, el('div', {}, info, el('div', { className: 'form-actions' }, cancel, confirm)), opener,
    { initialFocus: cancel, descriptionId: info.id, onDestroy: () => finish(false) })
  return { promise, destroy: () => finish(false) }
}
