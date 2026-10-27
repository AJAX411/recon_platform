const API_ROOT = '/api/v1'
let csrfToken = null

export class ApiError extends Error {
  constructor(message, status, writeAttempted = false) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    // True only after fetch was invoked for a mutating request, never for CSRF preflight.
    this.writeAttempted = writeAttempted
  }
}

export function clearCsrf() { csrfToken = null }

export async function request(path, { method = 'GET', body, signal, idempotencyKey, responseMeta = false } = {}) {
  if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Ruta API inválida')
  const verb = method.toUpperCase()
  const mutating = !['GET', 'HEAD'].includes(verb)
  if (idempotencyKey !== undefined && (verb !== 'POST' || path !== '/eventos-acceso/manual'
    || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(idempotencyKey))) {
    throw new Error('Clave idempotente inválida para esta operación')
  }
  if (mutating && !csrfToken) await fetchCsrf()
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (mutating) headers['X-CSRF-Token'] = csrfToken
  if (idempotencyKey !== undefined) headers['Idempotency-Key'] = idempotencyKey

  let response
  try {
    response = await fetch(`${API_ROOT}${path}`, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'same-origin', cache: 'no-store', signal,
    })
  } catch {
    throw new ApiError('No se pudo conectar con la plataforma. Inténtalo de nuevo.', 0, mutating)
  }
  let data = null
  try { data = await response.json() } catch { /* El servidor puede responder sin JSON. */ }
  if (!response.ok) throw new ApiError(data?.error || `La solicitud falló (${response.status}).`, response.status, mutating)
  const rotated = response.headers.get('X-CSRF-Token')
  if (rotated) csrfToken = rotated
  return responseMeta ? { data, status: response.status,
    idempotentReplay: response.headers.get('Idempotent-Replay') === 'true' } : data
}

export async function fetchCsrf() {
  const data = await request('/auth/csrf')
  if (typeof data?.csrf_token !== 'string' || !data.csrf_token) {
    throw new ApiError('No se recibió el token CSRF.', 0)
  }
  csrfToken = data.csrf_token
  return csrfToken
}
