import { beforeEach, describe, expect, it, vi } from 'vitest'
import { clearCsrf, request } from '../api/http.js'
import { login, logout } from '../api/auth.js'

const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), {
  status, headers: { 'Content-Type': 'application/json', ...headers },
})

describe('cliente HTTP y sesión', () => {
  beforeEach(() => { clearCsrf(); vi.stubGlobal('fetch', vi.fn()) })

  it('obtiene CSRF, lo envía al login y usa el token rotado para logout', async () => {
    fetch.mockResolvedValueOnce(json({ csrf_token: 'anonimo' }))
      .mockResolvedValueOnce(json({ id_usuario: 2, login: 'cuenta.ficticia', rol: 'ADMINISTRADOR' }, 200, { 'X-CSRF-Token': 'rotado' }))
      .mockResolvedValueOnce(json({ estado: 'cerrada' }))
    await login('cuenta.ficticia', 'clave-ficticia')
    await logout()
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/auth/csrf')
    expect(fetch.mock.calls[1][1].headers['X-CSRF-Token']).toBe('anonimo')
    expect(fetch.mock.calls[1][1].credentials).toBe('same-origin')
    expect(fetch.mock.calls[2][1].headers['X-CSRF-Token']).toBe('rotado')
  })

  it('recupera CSRF tras recargar y expone el error exacto del servidor', async () => {
    fetch.mockResolvedValueOnce(json({ csrf_token: 'sesion-recuperada' }))
      .mockResolvedValueOnce(json({ error: 'El identificador de Persona ya existe.' }, 409))
    await expect(request('/personas', { method: 'POST', body: { primer_nombre: 'Prueba' } }))
      .rejects.toMatchObject({ status: 409, message: 'El identificador de Persona ya existe.' })
    expect(fetch.mock.calls[1][1].headers['X-CSRF-Token']).toBe('sesion-recuperada')
  })

  it('informa un fallo de conexión sin enviar una solicitud de escritura', async () => {
    fetch.mockRejectedValueOnce(new TypeError('network'))
    await expect(request('/personas', { method: 'POST', body: {} })).rejects.toMatchObject({ status: 0 })
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
