import { clearCsrf, fetchCsrf, request } from './http.js'

export const getCurrentUser = () => request('/auth/me')

export async function login(login, contrasena) {
  await fetchCsrf()
  return request('/auth/login', { method: 'POST', body: { login, contrasena } })
}

export async function logout() {
  const result = await request('/auth/logout', { method: 'POST' })
  clearCsrf()
  return result
}
