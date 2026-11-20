import { matchRoute } from './routes.js'

export function createRouter(render, { beforeLeave = () => true } = {}) {
  const events = new AbortController()
  let dispose = () => {}
  let position = Number.isInteger(history.state?.reconPosition) ? history.state.reconPosition : 0
  history.replaceState({ ...history.state, reconPosition: position }, '', location.href)
  let current = { url: location.href, state: history.state, position }
  let waiting = false
  let restoring = null
  let permittedPop = false
  let active = true
  function resolve() {
    dispose()
    dispose = () => {}
    const route = matchRoute(location.pathname)
    document.title = route.title + ' · Recon Facial'
    dispose = render(route, history.state || {}) || (() => {})
    document.getElementById('contenido')?.focus()
    position = Number.isInteger(history.state?.reconPosition) ? history.state.reconPosition : position
    current = { url: location.href, state: history.state, position }
  }
  function navigate(url, { replace = false, state = {} } = {}) {
    const target = new URL(url, location.href)
    if (target.origin !== location.origin || /^\/api\/v1(?:\/|$)/.test(target.pathname)) return false
    if (waiting) return false
    const apply = () => {
      if (!active) return
      if (!replace) position += 1
      history[replace ? 'replaceState' : 'pushState']({ ...state, reconPosition: position }, '', target.pathname + target.search + target.hash)
      resolve()
    }
    const accepted = beforeLeave('navigate')
    if (accepted === true) { apply(); return true }
    if (accepted && typeof accepted.then === 'function') {
      waiting = true
      void accepted.then((ok) => { waiting = false; if (ok) apply() })
    }
    return false
  }
  document.addEventListener('click', (event) => {
    const a = event.target.closest?.('a[href]')
    if (!a || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey
      || event.altKey || event.shiftKey || a.hasAttribute('download') || (a.target && a.target !== '_self')
      || a.getAttribute('href').startsWith('#')) return
    const target = new URL(a.href, location.href)
    if (target.origin !== location.origin || /^\/api\/v1(?:\/|$)/.test(target.pathname)) return
    event.preventDefault()
    navigate(target.href, { state: a.navigationState || {} })
  }, { signal: events.signal })
  window.addEventListener('recon:context', () => { current.state = history.state }, { signal: events.signal })
  window.addEventListener('popstate', () => {
    if (restoring) { const done = restoring; restoring = null; done(); return }
    if (permittedPop) { permittedPop = false; resolve(); return }
    const target = { url: location.href, state: history.state }
    const accepted = beforeLeave('navigate')
    if (accepted === true) { resolve(); return }
    const delta = Number.isInteger(target.state?.reconPosition) ? target.state.reconPosition - current.position : 0
    const restored = delta ? new Promise((done) => { restoring = done; history.go(-delta) })
      : Promise.resolve(history.replaceState(current.state, '', current.url))
    waiting = true
    void Promise.all([Promise.resolve(accepted), restored]).then(([ok]) => {
      waiting = false
      if (!active || !ok) return
      if (delta) { permittedPop = true; history.go(delta) }
      else { history.replaceState(target.state, '', target.url); resolve() }
    })
  }, { signal: events.signal })
  return { navigate, render: resolve, destroy: () => {
    active = false; events.abort(); dispose()
    const done = restoring; restoring = null; done?.()
  } }
}
