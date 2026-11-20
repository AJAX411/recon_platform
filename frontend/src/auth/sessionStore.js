/** Sesión del cliente en memoria: login/me definen identidad; épocas descartan respuestas antiguas y logout invalida lecturas. */
import { ROLES } from './permissions.js'

export function createSessionStore(api) {
  let state = { user: null, status: 'loading', error: '', epoch: 0 }
  let operation = 0
  let busy = false
  const listeners = new Set()
  const emit = () => { for (const listener of [...listeners]) listener(state) }
  const set = (values) => { state = { ...state, ...values }; emit() }
  const valid = (user) => Number.isSafeInteger(user?.id_usuario) && user.id_usuario > 0
    && typeof user.login === 'string' && ROLES.includes(user.rol)
  const identity = (user) => {
    if (!valid(user)) throw new Error('No se recibió una identidad válida.')
    // Solo auth/me o login definen estos datos; nunca se inventa correo ni Persona.
    return Object.freeze({ id_usuario: user.id_usuario, login: user.login, rol: user.rol })
  }
  function invalidate(status, error = '') {
    operation += 1
    api.http.clearCsrf()
    set({ user: null, status, error, epoch: state.epoch + 1 })
  }
  api.http.onFailure((error) => {
    if (error.status === 401) invalidate('anonymous')
    if (error.status === 403) invalidate('denied', error.message)
  })
  async function refresh() {
    const token = ++operation
    api.http.clearCsrf()
    set({ user: null, status: 'loading', error: '', epoch: state.epoch + 1 })
    try {
      const user = identity(await api.me())
      if (token === operation) set({ user, status: 'authenticated', error: '' })
    } catch (error) {
      if (token !== operation) return
      set({ user: null, status: error.status === 401 ? 'anonymous' : error.status === 403 ? 'denied' : 'error',
        error: error.status === 401 ? '' : error.message })
    }
  }
  async function signIn(login, password) {
    if (busy) return false
    busy = true
    const token = ++operation
    try {
      const user = identity(await api.login(login, password))
      if (token !== operation) return false
      set({ user, status: 'authenticated', error: '', epoch: state.epoch + 1 })
      return true
    } finally { busy = false }
  }
  async function signOut() {
    if (busy) return false
    busy = true
    const token = ++operation
    try {
      try { await api.logout() } catch (error) {
        if (error.status === 403 && token === operation) invalidate('denied', error.message)
        if (error.status !== 401) throw error
      }
      if (token !== operation) return false
      invalidate('anonymous')
      return true
    } finally { busy = false }
  }
  return {
    getState: () => state, refresh, signIn, signOut,
    expire: () => invalidate('anonymous'),
    subscribe: (listener) => { listeners.add(listener); return () => listeners.delete(listener) },
    destroy: () => { operation += 1; api.http.clearCsrf(); listeners.clear()
      state = { user: null, status: 'anonymous', error: '', epoch: state.epoch + 1 } },
  }
}
