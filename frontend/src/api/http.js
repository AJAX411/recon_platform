/** Cliente HTTP único: cookie same-origin, CSRF en memoria y lista cerrada de escrituras. Un resultado incierto no se reintenta automáticamente. */
export class ApiError extends Error {
  constructor(message, status, writeAttempted = false) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.writeAttempted = writeAttempted
  }
}

export function createHttp(fetcher = (...args) => globalThis.fetch(...args)) {
  let csrf = null
  let generation = 0
  let preparing = null
  let failureHandler = () => {}
  const clearCsrf = () => { csrf = null; preparing = null; generation += 1 }
  const stale = () => new DOMException('La sesión de esta lectura cambió.', 'AbortError')

  async function request(path, { method = 'GET', body, signal, responseMeta = false, idempotencyKey } = {}) {
    if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Ruta API inválida.')
    const verb = method.toUpperCase()
    const mutating = !['GET', 'HEAD'].includes(verb)
    // Lista cerrada de operaciones existentes. No hay DELETE ni escritura genérica.
    const allowedPost = /^\/(auth\/(login|logout)|personas|iam\/usuarios|puntos-acceso|dispositivos-edge|eventos-acceso\/manual)$/
    const allowedPatch = /^\/(personas\/[1-9]\d*(\/estado)?|iam\/usuarios\/[1-9]\d*\/(login|rol|estado)|puntos-acceso\/[1-9]\d*(\/estado)?|dispositivos-edge\/[1-9]\d*(\/(estado|modo))?)$/
    if (mutating && !(verb === 'POST' && allowedPost.test(path) || verb === 'PATCH' && allowedPatch.test(path))) {
      throw new ApiError('Método o ruta de escritura no autorizados.', 0, false)
    }
    const manual = verb === 'POST' && path === '/eventos-acceso/manual'
    if ((manual || idempotencyKey !== undefined) && (!manual
      || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(idempotencyKey || ''))) {
      throw new ApiError('Clave idempotente inválida para esta operación.', 0, false)
    }
    const epoch = generation
    if (mutating && !csrf) await fetchCsrf()
    if (epoch !== generation) throw stale()
    const headers = { Accept: 'application/json' }
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    if (mutating) headers['X-CSRF-Token'] = csrf
    if (manual) headers['Idempotency-Key'] = idempotencyKey
    let response
    try {
      response = await fetcher('/api/v1' + path, {
        method: verb, headers, credentials: 'same-origin', cache: 'no-store',
        body: body === undefined ? undefined : JSON.stringify(body), signal,
      })
    } catch (error) {
      if (mutating) throw new ApiError('No se pudo confirmar la respuesta de escritura.', 0, true)
      if (signal?.aborted || epoch !== generation || error.name === 'AbortError') throw stale()
      throw new ApiError('No se pudo conectar con la plataforma.', 0, mutating)
    }
    let data = null
    try { data = await response.json() } catch { /* Una respuesta sin JSON no confirma datos. */ }
    if (epoch !== generation || signal?.aborted) {
      if (mutating) throw new ApiError('La identidad cambió durante el envío; el resultado requiere revisión.', 0, true)
      throw stale()
    }
    if (!response.ok) {
      const failure = new ApiError(verb === 'POST' && path === '/iam/usuarios'
        ? 'No se pudo completar la operación de cuenta (HTTP ' + response.status + ').'
        : data?.error || 'La solicitud falló (' + response.status + ').', response.status, mutating)
      if (!path.startsWith('/auth/')) failureHandler(failure)
      throw failure
    }
    const rotated = response.headers.get('X-CSRF-Token')
    if (rotated) csrf = rotated
    return responseMeta ? { data, status: response.status,
      idempotentReplay: response.headers.get('Idempotent-Replay') === 'true' } : data
  }

  function fetchCsrf() {
    if (preparing) return preparing
    const epoch = generation
    const pending = request('/auth/csrf').then((data) => {
      if (epoch !== generation) throw stale()
      if (typeof data?.csrf_token !== 'string' || !data.csrf_token) {
        throw new ApiError('No se recibió el token CSRF.', 0, false)
      }
      csrf = data.csrf_token
      return csrf
    }).finally(() => { if (preparing === pending) preparing = null })
    preparing = pending
    return pending
  }

  return { request, fetchCsrf, clearCsrf, onFailure: (handler) => { failureHandler = handler } }
}
