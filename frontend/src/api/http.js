const API_ROOT = '/api/v1'
let csrfToken = null

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function clearCsrf() { csrfToken = null }

export async function request(path, { method = 'GET', body, signal } = {}) {
  if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Ruta API inválida')
  const mutating = !['GET', 'HEAD'].includes(method.toUpperCase())
  if (mutating && !csrfToken) await fetchCsrf()
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (mutating) headers['X-CSRF-Token'] = csrfToken

  let response
  try {
    response = await fetch(`${API_ROOT}${path}`, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'same-origin', cache: 'no-store', signal,
    })
  } catch {
    throw new ApiError('No se pudo conectar con la plataforma. Inténtalo de nuevo.', 0)
  }
  let data = null
  try { data = await response.json() } catch { /* El servidor puede responder sin JSON. */ }
  if (!response.ok) throw new ApiError(data?.error || `La solicitud falló (${response.status}).`, response.status)
  const rotated = response.headers.get('X-CSRF-Token')
  if (rotated) csrfToken = rotated
  return data
}

export async function fetchCsrf() {
  const data = await request('/auth/csrf')
  if (typeof data?.csrf_token !== 'string' || !data.csrf_token) {
    throw new ApiError('No se recibió el token CSRF.', 0)
  }
  csrfToken = data.csrf_token
  return csrfToken
}
