import { afterEach, describe, expect, it, vi } from 'vitest'
import { pages } from '../src/pages/index.js'
import { appAt, click, dashboardData, deferred, findButton, identity, response } from './helpers.js'

const cleanups = []
afterEach(() => { while (cleanups.length) cleanups.pop()() })
const dashboardCalls = (fetcher) => fetcher.mock.calls.filter(([url]) => url === '/api/v1/consultas/dashboard')
const firstMetric = () => document.querySelector('main .metric-card dd')?.textContent
async function mount(role, handler) {
  const result = await appAt('/', identity(role), {
    '/consultas/dashboard': handler,
    '*': (path) => path.startsWith('/puntos-acceso?') ? response({ puntos: [] }) : undefined,
  }, pages)
  cleanups.push(result.stop)
  await vi.waitFor(() => expect(document.querySelector('main')?.textContent).toContain('Última lectura'))
  return result
}
async function returnToHome(app) {
  app.router.navigate('/puntos-acceso')
  await vi.waitFor(() => expect(document.querySelector('main').textContent).toContain('No hay registros'))
  app.router.navigate('/')
}

describe('D-CP1 · UX-D02: relectura efectiva por navegación', () => {
  it.each(['SUPERADMIN', 'ADMINISTRADOR', 'OPERADOR'])('volver a Inicio relee y presenta datos nuevos para %s sin controles permanentes', async (role) => {
    const pending = deferred()
    let requests = 0
    const { app, fetcher } = await mount(role, () => ++requests === 1 ? response(dashboardData(role)) : pending.promise)
    expect(dashboardCalls(fetcher)).toHaveLength(1)
    await returnToHome(app)
    expect(dashboardCalls(fetcher)).toHaveLength(2)
    expect(document.querySelector('main').textContent).toContain('Actualizando datos anteriores')
    const next = dashboardData(role)
    if (role === 'OPERADOR') next.incidencias_hoy = 9
    else next.metricas.entradas_hoy = 11
    pending.resolve(response(next))
    await vi.waitFor(() => expect(firstMetric()).toBe(role === 'OPERADOR' ? '9' : '11'))
    expect(document.querySelector('main').textContent).not.toContain('Actualizando datos anteriores')
    expect(findButton('Actualizar')).toBeUndefined()
    expect([...document.querySelectorAll('main a')].some((a) => a.textContent === 'Ver historial')).toBe(false)
    expect(dashboardCalls(fetcher)).toHaveLength(2)
    expect(fetcher.mock.calls.every(([, options]) => options.method === 'GET')).toBe(true)
    if (role === 'OPERADOR') {
      expect(document.querySelector('main').textContent).not.toContain('Personas dentro')
      expect(document.querySelector('main').textContent).toContain('hora aproximada')
    }
  })

  it('un fallo al regresar conserva la lectura etiquetada; el reintento contextual obtiene datos nuevos', async () => {
    let requests = 0
    const { app, fetcher } = await mount('SUPERADMIN', () => {
      requests += 1
      const data = dashboardData()
      if (requests > 2) data.metricas.entradas_hoy = 12
      return requests === 2 ? response({ error: 'Consulta ficticia no disponible' }, 503) : response(data)
    })
    await returnToHome(app)
    await vi.waitFor(() => expect(document.querySelector('main').textContent).toContain('Datos desactualizados'))
    expect(firstMetric()).toBe('3')
    expect(document.querySelector('main').textContent).toContain('Consulta ficticia no disponible')
    expect(findButton('Actualizar')).toBeUndefined()
    expect(dashboardCalls(fetcher)).toHaveLength(2)
    click(findButton('Reintentar consulta'))
    await vi.waitFor(() => expect(firstMetric()).toBe('12'))
    expect(document.querySelector('main').textContent).not.toContain('Datos desactualizados')
    expect(dashboardCalls(fetcher)).toHaveLength(3)
    expect(fetcher.mock.calls.every(([, options]) => options.method === 'GET')).toBe(true)
  })

  it('una relectura antigua al regresar no repuebla Inicio después de expirar la identidad', async () => {
    const pending = deferred()
    let requests = 0
    const { app } = await mount('SUPERADMIN', () => ++requests === 1 ? response(dashboardData()) : pending.promise)
    await returnToHome(app)
    app.session.expire()
    await vi.waitFor(() => expect(location.pathname).toBe('/login'))
    pending.resolve(response(dashboardData()))
    await vi.waitFor(() => expect(document.querySelector('main').textContent).toContain('Iniciar sesión'))
    expect(document.querySelector('main .metric-grid')).toBeNull()
    expect(document.querySelector('main').textContent).not.toContain('Personas dentro')
  })
})
