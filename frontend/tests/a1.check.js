import { afterEach, describe, expect, it, vi } from 'vitest'
import { createHttp } from '../src/api/http.js'
import { createSessionStore } from '../src/auth/sessionStore.js'
import { createRouter } from '../src/router.js'
import { matchRoute, routes } from '../src/routes.js'
import { createDashboardStore } from '../src/dashboard/dashboardStore.js'
import userEvent from '@testing-library/user-event'
import { appAt, click, deferred, findButton, identity, mockServer, response } from './helpers.js'

const cleanups = []
afterEach(() => { while (cleanups.length) cleanups.pop()() })
const mount = async (...args) => {
  const result = await appAt(...args); cleanups.push(result.stop); return result
}
describe('A1 · núcleo Vanilla aislado', () => {
  it('reconoce 19 rutas, prioriza rutas fijas, distingue edición y fallback', () => {
    expect(routes).toHaveLength(19)
    expect(matchRoute('/personas/nueva').page).toBe('personCreate')
    expect(matchRoute('/personas/2/editar').permission).toBe('admin')
    expect(matchRoute('/personas/2').params.id).toBe('2')
    expect(matchRoute('/desconocida').page).toBe('notFound')
  })
  it('router usa history y popstate; limpia pantalla, título y listeners al destruir', () => {
    const dispose = vi.fn()
    const render = vi.fn(() => dispose)
    const router = createRouter(render)
    router.render()
    router.navigate('/personas', { state: { regreso: true } })
    expect(location.pathname).toBe('/personas')
    expect(history.state).toMatchObject({ regreso: true })
    expect(document.title).toContain('Personas')
    history.replaceState({}, '', '/puntos-acceso')
    window.dispatchEvent(new PopStateEvent('popstate'))
    expect(render.mock.calls.at(-1)[0].resource).toBe('points')
    router.destroy()
    const calls = render.mock.calls.length
    window.dispatchEvent(new PopStateEvent('popstate'))
    expect(render).toHaveBeenCalledTimes(calls)
    expect(dispose).toHaveBeenCalledTimes(3)
  })
  it.each([
    ['https://example.org/a', {}], ['/api/v1/auth/me', {}], ['/personas', { ctrlKey: true }],
    ['/personas', { metaKey: true }], ['/personas', { shiftKey: true }],
  ])('no intercepta navegación especial %s %o', (href, init) => {
    const router = createRouter(vi.fn())
    cleanups.push(router.destroy)
    // Se comprueba la decisión del router antes de impedir la navegación que JSDOM no implementa.
    document.addEventListener('click', (e) => {
      expect(e.defaultPrevented).toBe(false)
      e.preventDefault()
    }, { once: true })
    const a = document.createElement('a'); a.href = href; document.body.append(a)
    const e = new MouseEvent('click', { bubbles: true, cancelable: true, button: 0, ...init })
    a.dispatchEvent(e)
  })
  it.each(['download', 'target'])('no intercepta enlace con %s', (attribute) => {
    const router = createRouter(vi.fn()); cleanups.push(router.destroy)
    document.addEventListener('click', (e) => { expect(e.defaultPrevented).toBe(false); e.preventDefault() }, { once: true })
    const a = document.createElement('a'); a.href = '/personas'
    a.setAttribute(attribute, attribute === 'target' ? '_blank' : '')
    document.body.append(a)
    const e = new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 })
    a.dispatchEvent(e)
  })
  it('CSRF previo, rotación, credenciales same-origin/no-store y logout sin repetir POST', async () => {
    const { api, fetcher } = mockServer()
    await api.login('cuenta-ficticia', 'x'.repeat(12))
    await api.logout()
    expect(fetcher.mock.calls.map(([url]) => url)).toEqual(['/api/v1/auth/csrf', '/api/v1/auth/login', '/api/v1/auth/logout'])
    expect(fetcher.mock.calls[1][1]).toMatchObject({ credentials: 'same-origin', cache: 'no-store', method: 'POST',
      headers: { 'X-CSRF-Token': 'csrf-de-prueba' } })
    expect(fetcher.mock.calls[2][1].headers['X-CSRF-Token']).toBe('csrf-rotado-de-prueba')
  })
  it('bloquea escrituras no autorizadas y URL inválida antes de fetch', async () => {
    const fetcher = vi.fn()
    const http = createHttp(fetcher)
    for (const method of ['POST', 'PATCH', 'DELETE']) {
      await expect(http.request('/ruta-no-autorizada', { method })).rejects.toMatchObject({ writeAttempted: false })
    }
    await expect(http.request('//ajeno')).rejects.toThrow()
    expect(fetcher).not.toHaveBeenCalled()
  })
  it('fallo en CSRF es preflight; fallo posterior al login indica intento y no se reenvía', async () => {
    const fetcher = vi.fn().mockRejectedValueOnce(new Error('sin red'))
    const http = createHttp(fetcher)
    await expect(http.request('/auth/login', { method: 'POST' })).rejects.toMatchObject({ writeAttempted: false })
    expect(fetcher).toHaveBeenCalledTimes(1)
    fetcher.mockResolvedValueOnce(response({ csrf_token: 'solo-prueba' })).mockRejectedValueOnce(new Error('sin red'))
    await expect(http.request('/auth/login', { method: 'POST' })).rejects.toMatchObject({ writeAttempted: true })
    expect(fetcher).toHaveBeenCalledTimes(3)
  })
  it('login limpia contraseña de DOM al fallar y preserva error, sin almacenamiento', async () => {
    await mount('/login', null, { '/auth/login': () => response({ error: 'Credenciales inválidas.' }, 401) })
    document.querySelector('#login').value = 'cuenta-ficticia'
    document.querySelector('#contrasena').value = 'x'.repeat(12)
    document.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await vi.waitFor(() => expect(document.body.textContent).toContain('Credenciales inválidas.'))
    expect(document.querySelector('#contrasena').value).toBe('')
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })
  it('login exitoso y logout pasan por la sesión real del cliente con dobles', async () => {
    const { app } = await mount('/login', null)
    const form = document.querySelector('form')
    form.querySelector('#login').value = 'cuenta-ficticia'
    form.querySelector('#contrasena').value = 'x'.repeat(12)
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await vi.waitFor(() => expect(location.pathname).toBe('/'))
    expect(app.session.getState().user.rol).toBe('SUPERADMIN')
    click(findButton('cuenta-ficticia · SUPERADMIN'))
    click(findButton('Cerrar sesión'))
    await vi.waitFor(() => expect(location.pathname).toBe('/login'))
    expect(app.session.getState().user).toBeNull()
    expect(document.querySelector('.topbar')).toBeNull()
  })
  it.each([403, 503])('auth/me %s conserva denegación/error y no inventa anonimato', async (status) => {
    const { app } = await mount('/personas', identity(), { '/auth/me': () => response({ error: 'Sesión no disponible' }, status) })
    expect(app.session.getState().status).toBe(status === 403 ? 'denied' : 'error')
    expect(document.body.textContent).toContain('Sesión no disponible')
    expect(document.querySelector('form')).toBeNull()
  })
  it.each(['ADMINISTRADOR', 'OPERADOR'])('IAM no monta ni consulta por URL de %s', async (role) => {
    const view = vi.fn()
    const { fetcher } = await mount('/usuarios', identity(role), {}, { list: view })
    expect(view).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain('Acceso no permitido')
    expect(fetcher.mock.calls.some(([u]) => u.includes('/iam/'))).toBe(false)
  })
  it('OPERADOR no monta Persona/creaciones y las rutas B no escriben', async () => {
    const { app, fetcher } = await mount('/personas/nueva', identity('OPERADOR'))
    expect(document.body.textContent).toContain('Acceso no permitido')
    app.router.navigate('/eventos-acceso/manual')
    expect(matchRoute('/eventos-acceso/manual').page).toBe('manual')
    expect(document.querySelector('form')).toBeNull()
    expect(fetcher.mock.calls.every(([, o]) => o.method === 'GET')).toBe(true)
  })
  it('menú cuenta teclado/Escape/fuera, datos de me sin email y XSS textual, foco de modal', async () => {
    await mount('/', { ...identity(), login: '<img src=x onerror=alert(1)>' })
    const trigger = [...document.querySelectorAll('button')].find((b) => b.textContent.includes('<img'))
    expect(document.querySelector('img')).toBeNull()
    click(trigger)
    expect(trigger.getAttribute('aria-expanded')).toBe('true')
    click(findButton('Perfil'))
    expect(document.querySelector('dialog').textContent).toContain('<img')
    expect(document.querySelector('dialog').textContent).not.toContain('Correo')
    document.querySelector('dialog').dispatchEvent(new Event('cancel', { cancelable: true }))
    expect(document.activeElement).toBe(trigger)
    click(trigger)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(trigger.getAttribute('aria-expanded')).toBe('false')
    click(trigger); click(document.querySelector('main'))
    expect(trigger.getAttribute('aria-expanded')).toBe('false')
  })
  it('ignora un auth/me antiguo después de expirar sesión', async () => {
    const later = deferred()
    const { api } = mockServer(identity(), { '/auth/me': () => later.promise })
    const session = createSessionStore(api); cleanups.push(session.destroy)
    const request = session.refresh()
    session.expire()
    later.resolve(response(identity()))
    await request
    expect(session.getState().status).toBe('anonymous')
    expect(session.getState().user).toBeNull()
  })
  it('botón de cuenta responde a Enter/Espacio y el skip link lleva foco a main', async () => {
    await mount('/')
    const user = userEvent.setup()
    const trigger = findButton('cuenta-ficticia · SUPERADMIN')
    trigger.focus()
    await user.keyboard('{Enter}')
    expect(trigger.getAttribute('aria-expanded')).toBe('true')
    await user.keyboard('{Escape}')
    await user.keyboard(' ')
    expect(trigger.getAttribute('aria-expanded')).toBe('true')
    click(document.querySelector('.skip-link'))
    expect(document.activeElement).toBe(document.querySelector('main'))
  })
  it('CSRF concurrente deduplica solo preparación; limpiar sesión invalida respuesta antigua', async () => {
    const later = deferred()
    const fetcher = vi.fn(() => later.promise)
    const http = createHttp(fetcher)
    const first = http.fetchCsrf(), second = http.fetchCsrf()
    expect(first).toBe(second)
    http.clearCsrf()
    later.resolve(response({ csrf_token: 'antiguo-no-aplicable' }))
    await expect(first).rejects.toMatchObject({ name: 'AbortError' })
    expect(fetcher).toHaveBeenCalledTimes(1)
  })
  it('logout 403 retira datos privilegiados sin afirmar revocación exitosa', async () => {
    const { app } = await mount('/', identity(), { '/auth/logout': () => response({ error: 'CSRF denegado' }, 403) })
    click(findButton('cuenta-ficticia · SUPERADMIN'))
    click(findButton('Cerrar sesión'))
    await vi.waitFor(() => expect(app.session.getState().status).toBe('denied'))
    expect(app.session.getState().user).toBeNull()
    expect(document.querySelector('.topbar')).toBeNull()
    expect(document.body.textContent).toContain('CSRF denegado')
  })
  it('401/403 de lectura retiran datos de identidad y dashboard; 503 no expira', async () => {
    const server = mockServer()
    const session = createSessionStore(server.api)
    const dashboard = createDashboardStore(server.api, session)
    cleanups.push(() => { dashboard.destroy(); session.destroy() })
    await session.refresh(); await dashboard.refresh()
    server.fetcher.mockResolvedValueOnce(response({ error: 'No permitido' }, 403))
    await expect(server.api.person(7)).rejects.toMatchObject({ status: 403 })
    expect(session.getState().status).toBe('denied')
    expect(dashboard.getState().data).toBeNull()
    await session.refresh(); await dashboard.refresh()
    server.fetcher.mockResolvedValueOnce(response({ error: 'Temporal' }, 503))
    await expect(server.api.person(7)).rejects.toMatchObject({ status: 503 })
    expect(session.getState().status).toBe('authenticated')
    server.fetcher.mockResolvedValueOnce(response({ error: 'Caducada' }, 401))
    await expect(server.api.person(7)).rejects.toMatchObject({ status: 401 })
    expect(session.getState().user).toBeNull()
  })
})
