import { request } from './http.js'
import { pagePath } from './pagination.js'

export const getRoles = (signal) => request('/iam/roles', { signal })
export const listUsers = (_filters, offset = 0, limit = 20, signal) =>
  request(pagePath('/iam/usuarios', {}, offset, limit), { signal })
export const getUser = (id, signal) => request(`/iam/usuarios/${id}`, { signal })
export const createUser = (data) => request('/iam/usuarios', { method: 'POST', body: data })
export const changeUserRole = (id, rol) =>
  request(`/iam/usuarios/${id}/rol`, { method: 'PATCH', body: { rol } })
export const changeUserState = (id, estado) =>
  request(`/iam/usuarios/${id}/estado`, { method: 'PATCH', body: { estado } })
