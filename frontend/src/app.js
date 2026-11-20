import { createApi } from './api/index.js'
import { createSessionStore } from './auth/sessionStore.js'
import { allows } from './auth/permissions.js'
import { createDashboardStore } from './dashboard/dashboardStore.js'
import { mountShell } from './components/Shell.js'
import { button, el, link, loading, message, page } from './components/dom.js'
import { createRouter } from './router.js'
import { mountLogin } from './pages/LoginPage.js'
import { createNavigation } from './navigation.js'
import { createWriteRegistry } from './components/writeFlow.js'
import { createManualStore } from './access/manualStore.js'

export function createApp(host, { api = createApi(), pages = {} } = {}) {
  const session = createSessionStore(api)
  const dashboard = createDashboardStore(api, session)
  const navigation = createNavigation()
  const writeRegistry = createWriteRegistry()
  const invalidateReadings = () => { if (session.getState().status === 'authenticated') void dashboard.invalidate() }
  const manual = createManualStore({ api, session, navigation, invalidateReadings })
  let shell = null
  let shellKey = ''
  function mainFor(state) {
    const key = state.status === 'authenticated' ? state.user.id_usuario + ':' + state.user.rol + ':' + state.epoch : ''
    if (shell && key !== shellKey) { shell.destroy(); shell = null }
    if (key && !shell) { shell = mountShell(host, session, dashboard, navigation, manual); shellKey = key }
    if (shell) return shell.main
    const main = el('main', { id: 'contenido', tabIndex: -1, className: 'centered-state' })
    const skip = link('#contenido', 'Saltar al contenido principal', { className: 'skip-link' })
    skip.addEventListener('click', (event) => { event.preventDefault(); main.focus() })
    host.replaceChildren(skip, main)
    return main
  }
  const router = createRouter((route, navigationState) => {
    const state = session.getState()
    const container = mainFor(state)
    container.replaceChildren()
    shell?.setPath(location.pathname)
    if (state.status === 'loading') { container.append(loading()); return }
    if (['error', 'denied'].includes(state.status)) {
      container.append(message(state.error || 'No se pudo comprobar la sesión.'),
        button('Reintentar sesión', session.refresh))
      return
    }
    if (state.status === 'authenticated' && route.page === 'login') {
      queueMicrotask(() => { if (session.getState().status === 'authenticated' && location.pathname === '/login') router.navigate('/', { replace: true }) })
      return
    }
    if (state.status !== 'authenticated' && !['login', 'notFound'].includes(route.page)) {
      queueMicrotask(() => { if (session.getState().status === 'anonymous') router.navigate('/login', { replace: true }) })
      return
    }
    if (state.user && route.permission !== 'public' && !allows(state.user, route.permission)) {
      container.append(page('Acceso no permitido'), message('Tu rol no permite consultar esta pantalla.'),
        link('/', 'Volver a Inicio'))
      return
    }
    if (route.page === 'login') return mountLogin({ container, session })
    if (route.page === 'notFound') {
      container.append(page('Página no encontrada'), link(state.user ? '/' : '/login', state.user ? 'Volver a Inicio' : 'Ir a iniciar sesión'))
      return
    }
    return pages[route.page]?.({ container, params: route.params, route, navigationState, session, api, dashboard,
      navigation, manual, writeRegistry, invalidateReadings, navigate: router.navigate }) || (() => {})
  }, { beforeLeave: navigation.check })
  const unsubscribe = session.subscribe(router.render)
  router.render()
  void session.refresh()
  return { session, dashboard, router, navigation, manual, destroy: () => {
    unsubscribe(); router.destroy(); navigation.destroy(); shell?.destroy(); manual.destroy(); dashboard.destroy(); session.destroy(); writeRegistry.clear(); host.replaceChildren()
  } }
}
