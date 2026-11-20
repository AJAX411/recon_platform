/** Resumen por identidad: valida la proyección de rol, invalida tras mutaciones y revalida por actividad sin polling. */
export function createDashboardStore(api, session) {
  let state = { data: null, status: 'loading', error: '' }
  let identity = ''
  let pending = null
  let controller = null
  let version = 0
  let lastReadAt = 0
  const listeners = new Set()
  const emit = () => { for (const listener of [...listeners]) listener(state) }
  function reset() {
    version += 1
    controller?.abort()
    pending = null
    state = { data: null, status: 'loading', error: '' }
    emit()
  }
  function refresh() {
    if (!identity) return Promise.resolve()
    if (pending) return pending
    lastReadAt = Date.now()
    controller = new AbortController()
    const signal = controller.signal
    const epoch = version
    const reduced = session.getState().user?.rol === 'OPERADOR'
    state = { ...state, status: 'loading', error: '' }
    emit()
    const task = api.dashboard(signal).then((data) => {
      if (signal.aborted || epoch !== version) return
      if (data?.alcance !== (reduced ? 'JORNADA_ACTUAL_REDUCIDA' : 'HISTORICO_ADMINISTRATIVO')) {
        throw new Error('No se recibió un resumen válido para esta sesión.')
      }
      // Una proyección reducida con campos administrativos se rechaza, no se reutiliza.
      if (reduced && (data.metricas || data.ultimos_movimientos?.some((row) =>
        Object.keys(row).some((key) => !['tipo_movimiento', 'resultado', 'hora_local_aproximada'].includes(key))))) {
        throw new Error('La proyección reducida contiene datos no permitidos.')
      }
      state = { data, status: 'success', error: '' }
      emit()
    }).catch((error) => {
      if (signal.aborted || epoch !== version) return
      state = { data: [401, 403].includes(error.status) ? null : state.data,
        status: 'error', error: error.message }
      emit()
    }).finally(() => { if (pending === task) pending = null })
    pending = task
    return task
  }
  const unsubscribe = session.subscribe((s) => {
    const next = s.status === 'authenticated' ? s.user.id_usuario + ':' + s.user.rol + ':' + s.epoch : ''
    if (next === identity) return
    identity = next
    reset()
    if (identity) void refresh()
  })
  // También funciona cuando se monta sobre una sesión ya comprobada.
  const s = session.getState()
  if (s.status === 'authenticated') {
    identity = s.user.id_usuario + ':' + s.user.rol + ':' + s.epoch
    void refresh()
  }
  // Revalidación por actividad, sin intervalos ni consultas repetidas al enfocar.
  const refocus = () => {
    if (document.visibilityState !== 'hidden' && Date.now() - lastReadAt >= 30_000) void refresh()
  }
  window.addEventListener('focus', refocus)
  document.addEventListener('visibilitychange', refocus)
  return { getState: () => state, refresh,
    invalidate: () => { version += 1; controller?.abort(); pending = null; return refresh() },
    subscribe: (listener) => { listeners.add(listener); return () => listeners.delete(listener) },
    destroy: () => {
      window.removeEventListener('focus', refocus)
      document.removeEventListener('visibilitychange', refocus)
      unsubscribe(); identity = ''; reset(); listeners.clear()
    } }
}
