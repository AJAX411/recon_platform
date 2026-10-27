import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/useAuth.js'
import { registerManualAccess } from '../api/eventos.js'
import { PendingManualContext } from './pendingContext.js'

export function PendingManualProvider({ children }) {
  const { user, expire } = useAuth()
  const actorRef = useRef(user?.id_usuario)
  actorRef.current = user?.id_usuario
  const currentRef = useRef(null)
  const sendingRef = useRef(false)
  const [submission, setSubmission] = useState(null)

  const update = useCallback((value) => {
    currentRef.current = value
    setSubmission(value)
  }, [])

  const clear = useCallback(() => { update(null) }, [update])

  useEffect(() => {
    if (currentRef.current && currentRef.current.actorId !== user?.id_usuario) clear()
  }, [user?.id_usuario, clear])

  useEffect(() => {
    if (!submission || !['sending', 'uncertain', 'preflight', 'conflict'].includes(submission.phase)) return
    const warn = (event) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [submission])

  const send = useCallback(async (declaration) => {
    try {
      const response = await registerManualAccess(declaration.body, declaration.key)
      if (currentRef.current?.key !== declaration.key || actorRef.current !== declaration.actorId) return
      update({ ...declaration, phase: 'success', response, error: '' })
    } catch (failure) {
      if (currentRef.current?.key !== declaration.key || actorRef.current !== declaration.actorId) return
      if (failure.status === 401) {
        clear()
        expire()
        return
      }
      const attempted = Boolean(failure.writeAttempted)
      const phase = failure.status === 409 ? 'conflict'
        : [0, 503].includes(failure.status) && attempted ? 'uncertain'
          : [0, 503].includes(failure.status) && !attempted ? 'preflight' : 'rejected'
      const error = phase === 'uncertain'
        ? 'No se pudo confirmar si la declaración quedó registrada. Reintenta solo esta misma declaración o consulta con un administrador.'
        : phase === 'preflight'
          ? 'No se envió la declaración: no se pudo preparar la solicitud. Puedes reintentar la misma declaración.'
          : failure.message || 'No se pudo registrar la declaración.'
      update({ ...declaration, phase, error })
    } finally {
      sendingRef.current = false
    }
  }, [clear, expire, update])

  function start(body) {
    if (sendingRef.current || currentRef.current || !actorRef.current) return false
    let key
    try { key = globalThis.crypto.randomUUID() }
    catch {
      update({ actorId: actorRef.current, phase: 'localError',
        error: 'No se pudo crear una clave segura para la declaración.' })
      return false
    }
    const declaration = {
      actorId: actorRef.current, key,
      body: Object.freeze({
        id_persona: body.id_persona, id_punto_acceso: body.id_punto_acceso,
        tipo_movimiento: body.tipo_movimiento,
      }),
    }
    sendingRef.current = true
    update({ ...declaration, phase: 'sending' })
    void send(declaration)
    return true
  }

  function retry() {
    const declaration = currentRef.current
    if (sendingRef.current || !declaration || !['uncertain', 'preflight'].includes(declaration.phase)
      || actorRef.current !== declaration.actorId) return false
    sendingRef.current = true
    update({ ...declaration, phase: 'sending', error: '' })
    void send(declaration)
    return true
  }

  const visibleSubmission = submission?.actorId === user?.id_usuario ? submission : null
  return <PendingManualContext.Provider value={{ submission: visibleSubmission, start, retry, clear }}>
    {children}
  </PendingManualContext.Provider>
}
