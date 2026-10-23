import { request } from './http.js'

export function listPeople(filters = {}, offset = 0, limit = 20, signal) {
  const params = new URLSearchParams({ limite: String(limit), desplazamiento: String(offset) })
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value)
  return request(`/personas?${params}`, { signal })
}

export const getPerson = (id, signal) => request(`/personas/${id}`, { signal })
export const getPersonTypes = (signal) => request('/personas/tipos', { signal })
export const createPerson = (data) => request('/personas', { method: 'POST', body: data })
