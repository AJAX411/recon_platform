import { allows } from '../auth/permissions.js'
import { button, dataGrid, el, link, message } from './dom.js'
import { openDialog } from './Dialog.js'
import { icon } from './Icons.js'

export function mountShell(host, session, dashboard, navigation, manual) {
  const { user } = session.getState()
  const events = new AbortController()
  let dialog = () => {}
  const main = el('main', { id: 'contenido', tabIndex: -1, className: 'main-content' })
  const errorBox = el('div')
  const manualNotice = el('div')
  const badge = el('strong', { className: 'alert-badge', 'aria-hidden': 'true' })
  const bell = link('/eventos-acceso/alertas', '', { className: 'header-incidents header-alerts' })
  bell.replaceChildren(icon('bell'), badge)
  const menu = el('div', { className: 'account-menu', hidden: true, role: 'group', 'aria-label': 'Opciones de cuenta' })
  const trigger = button(user.login + ' · ' + user.rol, () => toggle(menu.hidden), {
    className: 'btn btn-outline-secondary', 'aria-expanded': 'false', 'aria-controls': 'account-menu',
  })
  menu.id = 'account-menu'
  function toggle(open) {
    menu.hidden = !open
    trigger.setAttribute('aria-expanded', String(open))
  }
  const account = button('Perfil', () => {
    toggle(false)
    dialog()
    dialog = openDialog('Perfil', dataGrid([
      ['Identificador', user.id_usuario], ['Usuario', user.login], ['Rol', user.rol],
    ]), trigger)
  })
  const logout = button('Cerrar sesión', async () => {
    logout.disabled = true
    errorBox.replaceChildren()
    try { if (await navigation.check('logout')) await session.signOut() }
    catch (error) { errorBox.replaceChildren(message(error.message)) }
    finally { logout.disabled = false }
  })
  menu.append(account, logout)
  const tools = el('div', { className: 'session-tools' }, bell, el('div', { className: 'account-tools' }, trigger, menu))
  const top = el('header', { className: 'topbar' }, el('div', { className: 'container-fluid topbar-inner' },
    link('/', 'Recon Facial', { className: 'brand' }), tools))
  const nav = el('nav', { className: 'side-nav', 'aria-label': 'Navegación principal' })
  for (const [url, name, permission] of [
    ['/', 'Inicio', 'all'], ['/personas', 'Personas', 'admin'], ['/usuarios', 'Usuarios', 'super'],
    ['/puntos-acceso', 'Puntos de Acceso', 'all'], ['/dispositivos-edge', 'Dispositivos Edge', 'all'],
    ['/eventos-acceso/manual', 'Registro manual', 'all'],
    ['/eventos-acceso/historial', 'Historial de accesos', 'all'],
  ]) if (allows(user, permission)) nav.append(link(url, name, { className: 'side-link' }))
  const skip = link('#contenido', 'Saltar al contenido principal', { className: 'skip-link' })
  skip.addEventListener('click', (event) => { event.preventDefault(); main.focus() })
  host.replaceChildren(skip, top, el('div', { className: 'workspace container-fluid' }, nav,
    el('div', { className: 'main-workspace' }, errorBox, manualNotice, main)))
  const updateManual = (state) => {
    manualNotice.replaceChildren(...(state && ['sending', 'preflight', 'uncertain', 'conflict', 'identityBlocked'].includes(state.phase)
      ? [message('Hay una declaración manual sin resolver en memoria.', 'warning'), link('/eventos-acceso/manual', 'Revisar declaración')] : []))
  }
  const unsubscribeManual = manual.subscribe(updateManual)
  updateManual(manual.getState())
  document.addEventListener('click', (event) => {
    if (!menu.hidden && !menu.parentElement.contains(event.target)) toggle(false)
  }, { signal: events.signal })
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !menu.hidden) { toggle(false); trigger.focus() }
  }, { signal: events.signal })
  menu.parentElement.addEventListener('focusout', (event) => {
    // En un cambio de foco nativo, activeElement puede ser BODY durante focusout.
    // El destino conocido dentro de la cuenta no debe ocultar el botón antes del click.
    if (event.relatedTarget && menu.parentElement.contains(event.relatedTarget)) return
    queueMicrotask(() => {
      if (!events.signal.aborted && !menu.parentElement.contains(document.activeElement)) toggle(false)
    })
  }, { signal: events.signal })
  function update(snapshot) {
    const count = snapshot.data?.incidencias_hoy
    const known = Number.isSafeInteger(count) && count >= 0
    badge.hidden = !known
    badge.textContent = known ? count > 99 ? '99+' : String(count) : ''
    const state = snapshot.status === 'error' ? snapshot.data ? 'Datos desactualizados' : 'Sin lectura disponible'
      : snapshot.status === 'loading' ? 'Actualizando' : ''
    bell.setAttribute('aria-label', 'Abrir alertas. ' + (known ? count + ' incidencias hoy. ' : 'Conteo no disponible. ') + state)
    bell.title = bell.getAttribute('aria-label')
  }
  const unsubscribe = dashboard.subscribe(update)
  update(dashboard.getState())
  return { main, setPath: (path) => {
    toggle(false)
    for (const a of nav.querySelectorAll('a')) {
      const href = a.getAttribute('href')
      const active = href === '/' ? path === '/' : path === href || path.startsWith(href + '/')
      a.classList.toggle('active', active)
      if (active) a.setAttribute('aria-current', 'page')
      else a.removeAttribute('aria-current')
    }
  }, destroy: () => { events.abort(); unsubscribe(); unsubscribeManual(); dialog(); host.replaceChildren() } }
}
