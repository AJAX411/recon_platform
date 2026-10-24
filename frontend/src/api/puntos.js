import { request } from './http.js'
import { pagePath } from './pagination.js'

export const listPoints = (filters = {}, offset = 0, limit = 20, signal) =>
  request(pagePath('/puntos-acceso', filters, offset, limit), { signal })
export const getPoint = (id, signal) => request(`/puntos-acceso/${id}`, { signal })
export const createPoint = (data) => request('/puntos-acceso', { method: 'POST', body: data })
export const editPoint = (id, data) => request(`/puntos-acceso/${id}`, { method: 'PATCH', body: data })
export const changePointState = (id, estado) =>
  request(`/puntos-acceso/${id}/estado`, { method: 'PATCH', body: { estado } })
