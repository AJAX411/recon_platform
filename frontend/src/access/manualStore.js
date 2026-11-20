/** Estado del registro manual: protege preflight/envío y reutiliza una clave idempotente ante incertidumbre, sin reenvío automático. */
import { ApiError } from '../api/http.js'
import { approximateTime } from './projections.js'

const protectedPhases = ['sending', 'preflight', 'uncertain', 'conflict']
const incidents = [null, 'ENTRADA_REPETIDA', 'SALIDA_REPETIDA', 'SALIDA_SIN_ENTRADA_DEL_DIA']
const ownerOf = (state) => state.status === 'authenticated' ? state.user.id_usuario + ':' + state.user.rol : ''
export function createManualStore({ api, session, navigation, invalidateReadings }) {
  let attempt = null
  let sending = false
  let alive = true
  const listeners = new Set()
  function visible() {
    if (!attempt || !ownerOf(session.getState())) return null
    if (ownerOf(session.getState()) !== attempt.owner) {
      return protectedPhases.includes(attempt.phase)
        ? { phase: 'identityBlocked', error: 'Hay una declaración bloqueada por cambio de identidad. No puede mostrarse ni reenviarse desde esta cuenta o rol. Requiere revisión con la identidad original.' } : null
    }
    let response = attempt.response
    if (response && session.getState().user.rol === 'OPERADOR') {
      const d = response.data
      response = { status: response.status, idempotentReplay: response.idempotentReplay,
        data: { tipo_movimiento: d.tipo_movimiento, resultado: d.resultado, metodo_registro: d.metodo_registro,
          hora_local_aproximada: approximateTime(d.fecha_hora_ocurrencia), tipo_incidencia_secuencia: d.tipo_incidencia_secuencia } }
    }
    return { phase: attempt.phase, key: attempt.key, body: attempt.body,
      actorId: attempt.actorId, error: attempt.error || '', response }
  }
  const emit = () => { if (alive) for (const listener of [...listeners]) listener(visible()) }
  const hasPending = () => Boolean(attempt && protectedPhases.includes(attempt.phase))
  const unsubscribe = session.subscribe(emit)
  const unregister = navigation.register((reason) => {
    if (reason === 'discard' || !hasPending()) return null
    if (attempt.phase === 'sending') return { allow: false, message: 'Hay una declaración manual en curso. Espera su resultado; no cierres ni repitas el envío.' }
    return { message: 'Hay una declaración manual sin resolver. Su clave solo se conserva en memoria; navegar o cerrar sesión no confirma el resultado. Al recargar se pierde. No declares otro movimiento equivalente sin revisar el caso.' }
  })
  function validate(result, declaration) {
    const d = result?.data
    if (![200, 201].includes(result?.status) || result.status === 200 && !result.idempotentReplay
      || result.status === 201 && result.idempotentReplay
      || !Number.isSafeInteger(d?.id_evento_acceso) || d.id_evento_acceso <= 0
      || d.id_persona !== declaration.body.id_persona || d.id_punto_acceso !== declaration.body.id_punto_acceso
      || d.tipo_movimiento !== declaration.body.tipo_movimiento || d.id_usuario_registrador !== declaration.actorId
      || d.resultado !== 'AUTORIZADO' || d.metodo_registro !== 'MANUAL' || d.id_dispositivo !== null
      || !incidents.includes(d.tipo_incidencia_secuencia)
      || typeof d.fecha_hora_ocurrencia !== 'string' || !/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(d.fecha_hora_ocurrencia)
      || !Number.isFinite(new Date(d.fecha_hora_ocurrencia).getTime())) {
      throw new ApiError('La respuesta no permite confirmar la declaración.', 0, true)
    }
  }
  async function send(declaration) {
    try {
      const result = await api.manual(declaration.body, declaration.key)
      validate(result, declaration)
      if (!alive || attempt?.key !== declaration.key) return
      attempt = { ...declaration, phase: 'success', response: result, error: '' }
      invalidateReadings()
    } catch (failure) {
      if (!alive || attempt?.key !== declaration.key) return
      const uncertain = failure.writeAttempted !== false
        && (!Number.isInteger(failure.status) || failure.status === 0 || failure.status >= 500)
      const phase = failure.status === 409 ? 'conflict'
        : uncertain ? 'uncertain'
          : [0, 503].includes(failure.status) && failure.writeAttempted === false ? 'preflight' : 'rejected'
      attempt = { ...declaration, phase, error: phase === 'uncertain'
        ? 'Resultado incierto: no se pudo confirmar el registro. Reintenta explícitamente solo esta misma declaración o solicita revisión.'
        : phase === 'preflight' ? 'No se envió la declaración: falló su preparación CSRF. Puedes reintentar la misma solicitud.'
          : phase === 'conflict' ? 'Conflicto 409: la clave no confirma esta declaración. No se reintentará automáticamente.'
            : failure.message || 'La declaración fue rechazada.' }
    } finally { sending = false; emit() }
  }
  function start(body) {
    const current = session.getState(), owner = ownerOf(current)
    if (sending || !owner || hasPending() || attempt?.owner === owner) return false
    if (!body || Object.keys(body).sort().join(',') !== 'id_persona,id_punto_acceso,tipo_movimiento'
      || !Number.isSafeInteger(body.id_persona) || body.id_persona <= 0
      || !Number.isSafeInteger(body.id_punto_acceso) || body.id_punto_acceso <= 0
      || !['ENTRADA', 'SALIDA'].includes(body.tipo_movimiento)) return false
    let key
    try {
      key = crypto.randomUUID()
      if (!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(key)) throw new Error()
    } catch {
      attempt = { owner, actorId: current.user.id_usuario, phase: 'localError', error: 'No se pudo crear una clave segura. No se envió ninguna declaración.' }
      emit(); return false
    }
    attempt = { owner, actorId: current.user.id_usuario, key,
      body: Object.freeze({ id_persona: body.id_persona, id_punto_acceso: body.id_punto_acceso, tipo_movimiento: body.tipo_movimiento }),
      phase: 'sending' }
    sending = true
    emit()
    void send(attempt)
    return true
  }
  function retry() {
    if (sending || !attempt || attempt.owner !== ownerOf(session.getState()) || !['preflight', 'uncertain'].includes(attempt.phase)) return false
    sending = true
    attempt = { ...attempt, phase: 'sending', error: '' }
    emit()
    void send(attempt)
    return true
  }
  function clear({ confirmed = false } = {}) {
    if (sending || !attempt || attempt.owner !== ownerOf(session.getState())
      || ['sending', 'uncertain'].includes(attempt.phase)
      || ['preflight', 'conflict'].includes(attempt.phase) && !confirmed) return false
    attempt = null; emit(); return true
  }
  return { start, retry, clear, getState: visible, hasPending,
    subscribe: (listener) => { listeners.add(listener); return () => listeners.delete(listener) },
    destroy: () => { alive = false; unsubscribe(); unregister(); listeners.clear(); attempt = null } }
}
