import { request } from './http.js'
import { pagePath } from './pagination.js'

export const listDevices = (filters = {}, offset = 0, limit = 20, signal) =>
  request(pagePath('/dispositivos-edge', filters, offset, limit), { signal })
export const getDevice = (id, signal) => request(`/dispositivos-edge/${id}`, { signal })
export const createDevice = (data) => request('/dispositivos-edge', { method: 'POST', body: data })
export const editDevice = (id, nombre) =>
  request(`/dispositivos-edge/${id}`, { method: 'PATCH', body: { nombre } })
export const changeDeviceState = (id, estado) =>
  request(`/dispositivos-edge/${id}/estado`, { method: 'PATCH', body: { estado } })
export const changeDeviceMode = (id, modo_operacion) =>
  request(`/dispositivos-edge/${id}/modo`, { method: 'PATCH', body: { modo_operacion } })
