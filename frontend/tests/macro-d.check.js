import { afterEach, expect, it, vi } from 'vitest'
import { appAt, click, deferred, findButton, response } from './helpers.js'
import { businessApp, dialogButton, input, submit, waitText, writes } from './businessHelpers.js'

const cleanup = []
afterEach(() => { while (cleanup.length) cleanup.pop()() })
async function login(handlers = {}) {
  const mounted = await appAt('/login', null, handlers)
  cleanup.push(mounted.stop)
  return mounted
}
async function user(path = '/usuarios/7', role = 'SUPERADMIN', overrides = {}) {
  const mounted = await businessApp(path, role, overrides)
  cleanup.push(mounted.stop)
  await waitText(role === 'SUPERADMIN' ? 'Referencia interna' : 'Acceso no permitido')
  return mounted
}

it('login institucional: etiquetas, autocompletado, ojo inline tres veces y foco conservado', async () => {
  await login()
  expect(document.querySelector('.login-aside h1').textContent).toBe('Bienvenido')
  expect(document.querySelector('.login-panel h2').textContent).toBe('Iniciar sesión')
  const password = input('contrasena', 'secreto-ficticio-no-real')
  expect(password.autocomplete).toBe('current-password')
  expect(document.querySelector('#login').autocomplete).toBe('username')
  const toggle = document.querySelector('.password-field button')
  expect(toggle.type).toBe('button')
  password.focus(); password.setSelectionRange(2, 4)
  for (const type of ['text', 'password', 'text']) {
    click(toggle)
    expect(password.type).toBe(type)
    expect(password.value).toBe('secreto-ficticio-no-real')
    expect(document.activeElement).toBe(password)
    expect(password.selectionStart).toBe(2)
    expect(toggle.getAttribute('aria-pressed')).toBe(String(type === 'text'))
    expect(toggle.getAttribute('aria-label')).toBe(type === 'text' ? 'Ocultar contraseña' : 'Mostrar contraseña')
    expect(toggle.querySelector('svg')).not.toBeNull()
  }
})

it('login vacío aplica validación nativa; carga bloquea doble envío; error limpia y vuelve a ocultar', async () => {
  const pending = deferred()
  const { fetcher } = await login({ '/auth/login': () => pending.promise })
  const form = document.querySelector('main form')
  expect(form.checkValidity()).toBe(false)
  input('login', 'operador.ficticio'); input('contrasena', 'clave-ficticia')
  click(document.querySelector('.password-toggle'))
  submit(); submit()
  await vi.waitFor(() => expect(fetcher.mock.calls.filter(([url]) => url.endsWith('/auth/login'))).toHaveLength(1))
  expect(findButton('Ingresando…').disabled).toBe(true)
  expect(document.querySelector('.password-toggle').disabled).toBe(true)
  expect(form.getAttribute('aria-busy')).toBe('true')
  pending.resolve(response({ error: 'Credenciales inválidas.' }, 401))
  await waitText('Credenciales inválidas.')
  expect(document.querySelector('#contrasena').value).toBe('')
  expect(document.querySelector('#contrasena').type).toBe('password')
  expect(document.querySelector('main').textContent).not.toContain('clave-ficticia')
})

it('Editar usuario guarda solo login, normalizado; refresca sin cambiar rol, estado o credencial', async () => {
  const { fetcher, state } = await user()
  click(findButton('Editar usuario'))
  expect(document.querySelector('#login').value).toBe('operador-ficticio')
  expect(document.querySelector('#rol')).toBeNull()
  input('login', ' NUEVO.LOGIN '); submit()
  expect(writes(fetcher)).toHaveLength(0)
  click(dialogButton('Confirmar'))
  await waitText('Operación confirmada')
  expect(state.users[7]).toMatchObject({ login: 'nuevo.login', rol: 'OPERADOR', estado: 'ACTIVO' })
  expect(writes(fetcher)).toHaveLength(1)
  expect(writes(fetcher)[0][0]).toBe('/api/v1/iam/usuarios/7/login')
  expect(JSON.parse(writes(fetcher)[0][1].body)).toEqual({ login: 'nuevo.login' })
  expect(document.querySelector('h2').textContent).toBe('nuevo.login')
})

it('cancelar y descartar edición no escribe; validación local bloquea usuario inválido', async () => {
  const { fetcher } = await user()
  click(findButton('Editar usuario')); input('login', 'ab'); submit()
  expect(document.querySelector('#login').getAttribute('aria-invalid')).toBe('true')
  expect(document.querySelector('dialog')).toBeNull()
  input('login', 'otro.usuario'); click(findButton('Cancelar edición'))
  click(dialogButton('Descartar cambios'))
  await vi.waitFor(() => expect(document.querySelector('#login')).toBeNull())
  expect(writes(fetcher)).toHaveLength(0)
})

it.each([409, 503])('error HTTP %s en edición conserva el valor y no escribe rol ni reintenta', async (status) => {
  const { fetcher, state } = await user('/usuarios/7', 'SUPERADMIN', {
    '/iam/usuarios/7/login': () => response({ error: 'El identificador de login ya existe.' }, status),
  })
  click(findButton('Editar usuario')); input('login', 'ocupado.usuario'); submit(); click(dialogButton('Confirmar'))
  await waitText(status === 409 ? 'El identificador de login ya existe.' : 'No se pudo confirmar si la operación quedó guardada')
  expect(document.querySelector('#login').value).toBe('ocupado.usuario')
  expect(state.users[7].login).toBe('operador-ficticio')
  expect(writes(fetcher)).toHaveLength(1)
  if (status === 503) expect(findButton('Guardar cambios').disabled).toBe(true)
})

it.each(['ADMINISTRADOR', 'OPERADOR'])('%s no muestra editor ni solicita cuentas por ruta directa', async (role) => {
  const { fetcher } = await user('/usuarios/7', role)
  expect(findButton('Editar usuario')).toBeUndefined()
  expect(fetcher.mock.calls.some(([url]) => url.startsWith('/api/v1/iam/usuarios'))).toBe(false)
})

it('SUPERADMIN inicial no muestra edición, rol ni desactivación', async () => {
  await user('/usuarios/1')
  expect(findButton('Editar usuario')).toBeUndefined()
  expect(findButton('Cambiar rol')).toBeUndefined()
  expect(findButton('Desactivar')).toBeUndefined()
})

it.each(['SUPERADMIN', 'ADMINISTRADOR', 'OPERADOR'])('jornada %s sin sufijo decorativo, mantiene fecha y zona funcional', async (role) => {
  const mounted = await businessApp('/', role); cleanup.push(mounted.stop)
  await waitText('Jornada 17')
  expect(document.querySelector('.dashboard-context strong').textContent).not.toContain('Bogotá')
  expect(mounted.app.dashboard.getState().data.zona_horaria).toBe('America/Bogota')
  expect(mounted.app.dashboard.getState().data.jornada).toBe('2026-11-17')
})
