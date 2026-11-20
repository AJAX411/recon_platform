import { afterEach, beforeEach, vi } from 'vitest'

// JSDOM permite comprobar ciclo y foco, pero no top layer, inercia o zoom real.
const show = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const close = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')
beforeEach(() => {
  document.body.replaceChildren()
  document.body.style.cssText = ''
  document.documentElement.style.cssText = ''
  history.replaceState({}, '', '/login')
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Red real prohibida en estas pruebas.') }))
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value() { this.open = true } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value() { this.open = false } })
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  if (show) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', show)
  else delete HTMLDialogElement.prototype.showModal
  if (close) Object.defineProperty(HTMLDialogElement.prototype, 'close', close)
  else delete HTMLDialogElement.prototype.close
})
