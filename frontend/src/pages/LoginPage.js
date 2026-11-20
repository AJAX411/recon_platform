/** Login institucional y ojo inline: conserva foco, bloquea doble envío y limpia la contraseña en error, fin de intento o desmontaje. */
import { button, el, message } from '../components/dom.js'
import { icon } from '../components/Icons.js'

export function mountLogin({ container, session }) {
  const login = el('input', { id: 'login', name: 'login', className: 'form-control', required: true, maxLength: 100, autocomplete: 'username' })
  const password = el('input', { id: 'contrasena', name: 'contrasena', className: 'form-control', required: true, type: 'password', autocomplete: 'current-password' })
  const feedback = el('div')
  const toggle = button('', () => {
    const focused = document.activeElement
    const start = password.selectionStart, end = password.selectionEnd
    const shown = password.type === 'password'
    password.type = shown ? 'text' : 'password'
    toggle.replaceChildren(icon(shown ? 'eye-off' : 'eye'))
    toggle.setAttribute('aria-label', shown ? 'Ocultar contraseña' : 'Mostrar contraseña')
    toggle.setAttribute('aria-pressed', String(shown))
    if (focused === password) { password.focus(); password.setSelectionRange(start, end) }
  }, { className: 'password-toggle', 'aria-label': 'Mostrar contraseña', 'aria-controls': password.id, 'aria-pressed': 'false' })
  toggle.append(icon('eye'))
  const submit = el('button', { type: 'submit', className: 'btn btn-primary login-submit' }, 'Ingresar')
  const form = el('form', {}, el('label', { htmlFor: 'login' }, 'Usuario'), login,
    el('label', { htmlFor: 'contrasena' }, 'Contraseña'), el('div', { className: 'password-field' }, password, toggle), submit)
  let busy = false
  let active = true
  form.addEventListener('submit', async (event) => {
    event.preventDefault()
    if (busy) return
    busy = true
    submit.disabled = true
    toggle.disabled = true
    form.setAttribute('aria-busy', 'true')
    submit.textContent = 'Ingresando…'
    feedback.replaceChildren()
    try { await session.signIn(login.value.trim(), password.value) }
    catch (error) { if (active) feedback.replaceChildren(message(error.message)) }
    finally {
      password.value = ''
      password.type = 'password'
      toggle.replaceChildren(icon('eye'))
      toggle.setAttribute('aria-label', 'Mostrar contraseña')
      toggle.setAttribute('aria-pressed', 'false')
      submit.disabled = false
      toggle.disabled = false
      form.setAttribute('aria-busy', 'false')
      submit.textContent = 'Ingresar'
      busy = false
    }
  })
  container.classList.add('login-host')
  container.replaceChildren(el('div', { className: 'login-page' },
    el('section', { className: 'login-aside', 'aria-labelledby': 'login-purpose' },
      el('div', { className: 'login-wordmark' }, 'Recon Facial', el('span', {}, 'Plataforma web')),
      el('div', { className: 'login-introduction' }, el('p', { className: 'eyebrow light' }, 'Gestión institucional'),
        el('h1', { id: 'login-purpose' }, 'Bienvenido'),
        el('p', { className: 'login-description' }, 'Gestiona personas, puntos de acceso y movimientos registrados desde un solo espacio.'),
        el('div', { className: 'login-purpose' }, ['Personas', 'Puntos de acceso', 'Movimientos'].map((text) => el('span', {}, text)))),
      el('div', { className: 'login-geometry', 'aria-hidden': 'true' }, el('i'), el('i'), el('i'))),
    el('section', { className: 'login-panel', 'aria-labelledby': 'login-title' },
      el('div', { className: 'login-card' }, el('p', { className: 'eyebrow' }, 'Tu espacio de trabajo'),
        el('h2', { id: 'login-title' }, 'Iniciar sesión'), el('p', { className: 'muted' }, 'Acceso para cuentas autorizadas.'), feedback, form))))
  return () => { active = false; password.value = ''; password.type = 'password'; container.classList.remove('login-host'); form.remove() }
}
