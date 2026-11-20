import { button, el, message } from '../components/dom.js'

export function mountLogin({ container, session }) {
  const login = el('input', { id: 'login', name: 'login', className: 'form-control', required: true, maxLength: 100, autocomplete: 'username' })
  const password = el('input', { id: 'contrasena', name: 'contrasena', className: 'form-control', required: true, type: 'password', autocomplete: 'current-password' })
  const feedback = el('div')
  const toggle = button('Mostrar contraseña', () => {
    const shown = password.type === 'password'
    password.type = shown ? 'text' : 'password'
    toggle.textContent = shown ? 'Ocultar contraseña' : 'Mostrar contraseña'
    toggle.setAttribute('aria-pressed', String(shown))
  }, { 'aria-controls': password.id, 'aria-pressed': 'false' })
  const submit = el('button', { type: 'submit', className: 'btn btn-primary' }, 'Ingresar')
  const form = el('form', {}, el('label', { htmlFor: 'login' }, 'Usuario'), login,
    el('label', { htmlFor: 'contrasena' }, 'Contraseña'), password, toggle, submit)
  let busy = false
  let active = true
  form.addEventListener('submit', async (event) => {
    event.preventDefault()
    if (busy) return
    busy = true
    submit.disabled = true
    toggle.disabled = true
    feedback.replaceChildren()
    try { await session.signIn(login.value.trim(), password.value) }
    catch (error) { if (active) feedback.replaceChildren(message(error.message)) }
    finally {
      password.value = ''
      password.type = 'password'
      toggle.textContent = 'Mostrar contraseña'
      toggle.setAttribute('aria-pressed', 'false')
      submit.disabled = false
      toggle.disabled = false
      busy = false
    }
  })
  container.replaceChildren(el('section', { className: 'login-card' }, el('h1', {}, 'Iniciar sesión'),
    el('p', {}, 'Recon Facial · Acceso para cuentas autorizadas.'), feedback, form))
  return () => { active = false; password.value = ''; form.remove() }
}
