/** Adaptador de endpoints /api/v1: valida IDs y confirmación de escrituras; no decide permisos del servidor. */
import { ApiError, createHttp } from './http.js'
import { pagePath } from './pagination.js'
import { adminFiltersToApi } from '../access/format.js'

export function createApi(fetcher) {
  const http = createHttp(fetcher)
  const collection = (path, filters, offset, signal) =>
    http.request(pagePath(path, filters, offset, 20), { signal })
  const detail = (path, id, signal) => {
    if (!/^[1-9]\d*$/.test(String(id))) throw new Error('El identificador no es válido.')
    return http.request(path + '/' + id, { signal })
  }
  const idPath = (base, id, suffix = '') => {
    if (!Number.isSafeInteger(Number(id)) || !/^[1-9]\d*$/.test(String(id))) throw new ApiError('Identificador inválido.', 0, false)
    return base + '/' + id + suffix
  }
  async function write(path, method, body, idKey, expectedId) {
    const result = await http.request(path, { method, body, responseMeta: true })
    if (result.status !== (method === 'POST' ? 201 : 200)
      || !Number.isSafeInteger(result.data?.[idKey]) || result.data[idKey] <= 0
      || expectedId !== undefined && result.data[idKey] !== Number(expectedId)) {
      throw new ApiError('La respuesta no permite confirmar el resultado de la operación.', 0, true)
    }
    for (const [key, value] of Object.entries(body)) {
      if (key === 'contrasena') continue
      const expected = key === 'login' ? value.trim().toLowerCase() : value
      if (result.data[key] !== expected) throw new ApiError('La respuesta no confirma los datos enviados.', 0, true)
    }
    return result.data
  }
  return {
    http,
    me: () => http.request('/auth/me'),
    login: async (login, contrasena) => {
      await http.fetchCsrf()
      return http.request('/auth/login', { method: 'POST', body: { login, contrasena } })
    },
    logout: async () => {
      const result = await http.request('/auth/logout', { method: 'POST' })
      http.clearCsrf()
      return result
    },
    dashboard: (signal) => http.request('/consultas/dashboard', { signal }),
    listPeople: (filters, offset, signal) => collection('/personas', filters, offset, signal),
    person: (id, signal) => detail('/personas', id, signal),
    personTypes: (signal) => http.request('/personas/tipos', { signal }),
    documentTypes: (signal) => http.request('/personas/tipos-documento', { signal }),
    listUsers: (_filters, offset, signal) => collection('/iam/usuarios', {}, offset, signal),
    user: (id, signal) => detail('/iam/usuarios', id, signal),
    listPoints: (filters, offset, signal) => collection('/puntos-acceso', filters, offset, signal),
    point: (id, signal) => detail('/puntos-acceso', id, signal),
    listDevices: (filters, offset, signal) => collection('/dispositivos-edge', filters, offset, signal),
    device: (id, signal) => detail('/dispositivos-edge', id, signal),
    history: (filters, offset, signal) => collection('/eventos-acceso/historial', adminFiltersToApi(filters), offset, signal),
    alerts: (filters, offset, signal) => collection('/eventos-acceso/alertas', adminFiltersToApi(filters), offset, signal),
    alertCounts: (signal) => http.request('/eventos-acceso/alertas', { signal }),
    incident: (id, signal) => detail('/eventos-acceso/incidencias', id, signal),
    roles: (signal) => http.request('/iam/roles', { signal }),
    createPerson: (body) => write('/personas', 'POST', body, 'id_persona'),
    updatePerson: (id, body) => write(idPath('/personas', id), 'PATCH', body, 'id_persona', id),
    personState: (id, estado) => write(idPath('/personas', id, '/estado'), 'PATCH', { estado }, 'id_persona', id),
    createUser: (body) => write('/iam/usuarios', 'POST', body, 'id_usuario'),
    userLogin: (id, login) => write(idPath('/iam/usuarios', id, '/login'), 'PATCH', { login }, 'id_usuario', id),
    userRole: (id, rol) => write(idPath('/iam/usuarios', id, '/rol'), 'PATCH', { rol }, 'id_usuario', id),
    userState: (id, estado) => write(idPath('/iam/usuarios', id, '/estado'), 'PATCH', { estado }, 'id_usuario', id),
    createPoint: (body) => write('/puntos-acceso', 'POST', body, 'id_punto_acceso'),
    updatePoint: (id, body) => write(idPath('/puntos-acceso', id), 'PATCH', body, 'id_punto_acceso', id),
    pointState: (id, estado) => write(idPath('/puntos-acceso', id, '/estado'), 'PATCH', { estado }, 'id_punto_acceso', id),
    createDevice: (body) => write('/dispositivos-edge', 'POST', body, 'id_dispositivo'),
    updateDevice: (id, nombre) => write(idPath('/dispositivos-edge', id), 'PATCH', { nombre }, 'id_dispositivo', id),
    deviceState: (id, estado) => write(idPath('/dispositivos-edge', id, '/estado'), 'PATCH', { estado }, 'id_dispositivo', id),
    deviceMode: (id, modo_operacion) => write(idPath('/dispositivos-edge', id, '/modo'), 'PATCH', { modo_operacion }, 'id_dispositivo', id),
    eligiblePeople: (criterio, valor, signal) => http.request('/eventos-acceso/personas-elegibles?'
      + new URLSearchParams({ criterio, valor }), { signal }),
    manual: (body, key) => http.request('/eventos-acceso/manual', {
      method: 'POST', body, idempotencyKey: key, responseMeta: true,
    }),
  }
}
