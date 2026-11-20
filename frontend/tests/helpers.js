import { vi } from 'vitest'
import { createApi } from '../src/api/index.js'
import { createApp } from '../src/app.js'

export const identity = (rol = 'SUPERADMIN', id_usuario = 1) => ({ id_usuario, login: 'cuenta-ficticia', rol })
export const response = (data, status = 200, headers = {}) => ({
  ok: status >= 200 && status < 300, status,
  json: async () => data, headers: { get: (key) => headers[key] ?? null },
})
export function deferred() {
  let resolve, reject
  const promise = new Promise((a, b) => { resolve = a; reject = b })
  return { promise, resolve, reject }
}
export function mockServer(user = identity(), handlers = {}) {
  const fetcher = vi.fn(async (url, options) => {
    const path = url.replace('/api/v1', '')
    if (handlers[path]) return handlers[path](options)
    if (handlers['*']) {
      const result = handlers['*'](path, options)
      if (result !== undefined) return result
    }
    if (path === '/auth/me') return response(user, user ? 200 : 401)
    if (path === '/auth/csrf') return response({ csrf_token: 'csrf-de-prueba' })
    if (path === '/auth/login') return response(identity(), 200, { 'X-CSRF-Token': 'csrf-rotado-de-prueba' })
    if (path === '/auth/logout') return response({ estado: 'cerrada' })
    if (path === '/consultas/dashboard') return response(dashboardData(user?.rol))
    throw new Error('Ruta sin doble explícito: ' + path)
  })
  return { fetcher, api: createApi(fetcher) }
}
export function dashboardData(rol = 'SUPERADMIN') {
  const reduced = rol === 'OPERADOR'
  return { alcance: reduced ? 'JORNADA_ACTUAL_REDUCIDA' : 'HISTORICO_ADMINISTRATIVO',
    jornada: '2026-11-17', generado_en: '2026-11-17T09:00:00-05:00', zona_horaria: 'America/Bogota',
    incidencias_hoy: 0, conteos_por_incidencia: {}, ultimos_movimientos: [],
    calidad_datos: reduced ? { cobertura: 'JORNADA_ACTUAL', precision_temporal: 'HORA' }
      : { motivo: 'Estimación del historial disponible.', personas_sin_historial: 2 },
    ...(!reduced ? { metricas: { entradas_hoy: 3, salidas_hoy: 2, dentro_segun_registros: null, personas_registradas: 5 } } : {}),
  }
}
export async function appAt(path, user = identity(), handlers = {}, pages = {}) {
  history.replaceState({}, '', path)
  const server = mockServer(user, handlers)
  const host = document.createElement('div')
  document.body.append(host)
  const app = createApp(host, { api: server.api, pages })
  await vi.waitFor(() => { if (app.session.getState().status === 'loading') throw new Error('Esperando sesión') })
  return { ...server, app, host, stop: () => app.destroy() }
}
export function click(node) { node.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 })) }
export const findButton = (text) => [...document.querySelectorAll('button')].find((n) => n.textContent === text)
