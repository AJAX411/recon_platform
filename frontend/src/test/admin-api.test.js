import { beforeEach, describe, expect, it, vi } from 'vitest'
import { clearCsrf, request } from '../api/http.js'
import { createUser, changeUserRole, listUsers } from '../api/usuarios.js'
import { changePointState, listPoints } from '../api/puntos.js'
import { changeDeviceMode, changeDeviceState, listDevices } from '../api/dispositivos.js'

const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json' },
})

describe('contratos HTTP administrativos', () => {
  beforeEach(() => { clearCsrf(); vi.stubGlobal('fetch', vi.fn()) })

  it('envía filtros y paginación exclusivamente por los recursos aprobados', async () => {
    fetch.mockResolvedValueOnce(json({ usuarios: [], limite: 20, desplazamiento: 20 }))
      .mockResolvedValueOnce(json({ puntos: [], limite: 20, desplazamiento: 0 }))
      .mockResolvedValueOnce(json({ dispositivos: [], limite: 20, desplazamiento: 0 }))
    await listUsers({}, 20)
    await listPoints({ codigo: 'PX' })
    await listDevices({ modo_operacion: 'SALIDA', id_punto_acceso: '7' })
    expect(fetch.mock.calls.map(([url]) => url)).toEqual([
      '/api/v1/iam/usuarios?limite=20&desplazamiento=20',
      '/api/v1/puntos-acceso?limite=20&desplazamiento=0&codigo=PX',
      '/api/v1/dispositivos-edge?limite=20&desplazamiento=0&modo_operacion=SALIDA&id_punto_acceso=7',
    ])
  })

  it('usa un único CSRF en escrituras sucesivas sin persistir la contraseña', async () => {
    const storage = vi.spyOn(Storage.prototype, 'setItem')
    fetch.mockResolvedValueOnce(json({ csrf_token: 'csrf-prueba' }))
      .mockResolvedValueOnce(json({ id_usuario: 2, login: 'cuenta.prueba', rol: 'OPERADOR', estado: 'ACTIVO' }, 201))
      .mockResolvedValueOnce(json({ id_usuario: 2, login: 'cuenta.prueba', rol: 'ADMINISTRADOR', estado: 'ACTIVO' }))
      .mockResolvedValueOnce(json({ id_punto_acceso: 7, estado: 'INACTIVO' }))
      .mockResolvedValueOnce(json({ id_dispositivo: 8, modo_operacion: 'SALIDA' }))
      .mockResolvedValueOnce(json({ id_dispositivo: 8, estado: 'ACTIVO' }))
    await createUser({ login: 'cuenta.prueba', contrasena: 'Clave-Ficticia-0007', rol: 'OPERADOR' })
    await changeUserRole(2, 'ADMINISTRADOR')
    await changePointState(7, 'INACTIVO')
    await changeDeviceMode(8, 'SALIDA')
    await changeDeviceState(8, 'ACTIVO')
    expect(fetch).toHaveBeenCalledTimes(6)
    for (const [, options] of fetch.mock.calls.slice(1)) {
      expect(options.headers['X-CSRF-Token']).toBe('csrf-prueba')
      expect(options.credentials).toBe('same-origin')
    }
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({
      login: 'cuenta.prueba', contrasena: 'Clave-Ficticia-0007', rol: 'OPERADOR',
    })
    expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual({ rol: 'ADMINISTRADOR' })
    expect(JSON.parse(fetch.mock.calls[3][1].body)).toEqual({ estado: 'INACTIVO' })
    expect(JSON.parse(fetch.mock.calls[4][1].body)).toEqual({ modo_operacion: 'SALIDA' })
    expect(fetch.mock.calls[4][0]).toBe('/api/v1/dispositivos-edge/8/modo')
    expect(JSON.parse(fetch.mock.calls[5][1].body)).toEqual({ estado: 'ACTIVO' })
    expect(fetch.mock.calls[5][0]).toBe('/api/v1/dispositivos-edge/8/estado')
    expect(storage).not.toHaveBeenCalled()
  })

  it.each([400, 401, 403, 404, 409, 503])('conserva el error %s del backend', async (status) => {
    fetch.mockResolvedValueOnce(json({ error: `Error de prueba ${status}` }, status))
    await expect(request('/iam/usuarios/99')).rejects.toMatchObject({ status, message: `Error de prueba ${status}` })
  })
})
