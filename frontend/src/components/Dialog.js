/** Ciclo del dialog nativo: foco inicial/retorno, Escape, Tab y bloqueo de scroll; destruir retira listeners. */
import { button, el } from './dom.js'
let dialogSequence = 0

export function openDialog(title, content, opener, { onDestroy = () => {}, initialFocus, descriptionId } = {}) {
  const modal = el('dialog', { className: 'detail-panel movement-detail', 'aria-modal': 'true' })
  const heading = el('h2', { id: 'dialog-title-' + (++dialogSequence) }, title)
  modal.setAttribute('aria-labelledby', heading.id)
  if (descriptionId) modal.setAttribute('aria-describedby', descriptionId)
  const close = button('×', destroy, { className: 'btn btn-outline-secondary movement-detail-close',
    'aria-label': 'Cerrar ' + title.toLowerCase() })
  modal.append(el('div', { className: 'detail-heading' }, heading, close), content)
  const root = document.documentElement
  const body = document.body
  const previous = [root.style.overflow, body.style.overflow, body.style.paddingRight]
  let destroyed = false
  function destroy() {
    if (destroyed) return
    destroyed = true
    if (modal.open) modal.close()
    modal.remove()
    root.style.overflow = previous[0]
    body.style.overflow = previous[1]
    body.style.paddingRight = previous[2]
    if (opener?.isConnected) opener.focus()
    onDestroy()
  }
  modal.addEventListener('cancel', (event) => { event.preventDefault(); destroy() })
  modal.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') { event.preventDefault(); destroy(); return }
    if (event.key !== 'Tab') return
    const controls = [...modal.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled)')]
    const first = controls[0], last = controls.at(-1)
    if ((event.shiftKey && document.activeElement === first) || (!event.shiftKey && document.activeElement === last)) {
      event.preventDefault()
      ;(event.shiftKey ? last : first)?.focus()
    }
  })
  document.body.append(modal)
  try {
    modal.showModal()
    const width = root.clientWidth > 0 ? Math.max(0, window.innerWidth - root.clientWidth) : 0
    if (width) body.style.paddingRight = ((Number.parseFloat(getComputedStyle(body).paddingRight) || 0) + width) + 'px'
    root.style.overflow = 'hidden'
    body.style.overflow = 'hidden'
    ;(initialFocus || close).focus()
  } catch (error) { destroy(); throw error }
  return destroy
}
