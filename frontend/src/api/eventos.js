import { ApiError, request } from './http.js'
import { pagePath } from './pagination.js'
import { adminFiltersToApi } from '../access/format.js'

const BASE = '/eventos-acceso'

export function searchEligiblePeople(criterio, valor, signal) {
  const query = new URLSearchParams({ criterio, valor: valor.trim() })
  return request(`${BASE}/personas-elegibles?${query}`, { signal })
}

export function listAccessHistory(filters = {}, offset = 0, limit = 20, signal) {
  return request(pagePath(`${BASE}/historial`, adminFiltersToApi(filters), offset, limit), { signal })
}

export function listAccessAlerts(filters = {}, offset = 0, limit = 20, signal) {
  return request(pagePath(`${BASE}/alertas`, adminFiltersToApi(filters), offset, limit), { signal })
}

export function getAccessAlertCounts(signal) {
  return request(`${BASE}/alertas`, { signal })
}

export function getAccessIncident(id, signal) {
  if (!/^[1-9]\d*$/.test(String(id))) throw new Error('Identificador inválido.')
  return request(`${BASE}/incidencias/${id}`, { signal })
}

export async function registerManualAccess(body, key) {
  const response = await request(`${BASE}/manual`, {
    method: 'POST', body, idempotencyKey: key, responseMeta: true,
  })
  if (![200, 201].includes(response.status) || !Number.isInteger(response.data?.id_evento_acceso)) {
    throw new ApiError('No se recibió una confirmación válida del registro.', 0, true)
  }
  return response
}
