import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ActivePointSelector } from '../access/ActivePointSelector.jsx'
import { EligiblePersonSelector } from '../access/EligiblePersonSelector.jsx'
import { INCIDENCE_LABELS, formatBogota } from '../access/format.js'
import { usePendingManual } from '../access/usePendingManual.js'
import { canManagePeople, useAuth } from '../auth/useAuth.js'
import { Alert } from '../components/Feedback.jsx'
import { Confirmation } from '../components/Confirmation.jsx'
import { DetailGrid } from '../components/DetailGrid.jsx'
import { SelectField } from '../components/Field.jsx'

export function AccessManualPage() {
  const { user } = useAuth()
  const { submission, start, retry, clear } = usePendingManual()
  const [person, setPerson] = useState(null)
  const [point, setPoint] = useState(null)
  const [movement, setMovement] = useState('')
  const [errors, setErrors] = useState({})
  const [confirming, setConfirming] = useState(false)
  const confirmTrigger = useRef(null)
  const outcomePanel = useRef(null)
  const focusAfterConfirm = useRef(false)
  const focusedOperation = useRef(null)
  const locked = Boolean(submission)

  useEffect(() => {
    if (!focusAfterConfirm.current || !submission) return
    const operation = submission.key || 'local-error'
    if (focusedOperation.current === operation) return
    focusedOperation.current = operation
    outcomePanel.current?.focus()
  }, [submission])

  function selectPerson(value) {
    setPerson(value)
    setErrors((current) => ({ ...current, person: '' }))
  }

  function selectPoint(value) {
    setPoint(value)
    setErrors((current) => ({ ...current, point: '' }))
  }

  function prepare() {
    const next = {}
    if (!person?.id_persona) next.person = 'Selecciona una Persona elegible.'
    if (!point?.id_punto_acceso) next.point = 'Selecciona un Punto activo.'
    if (!['ENTRADA', 'SALIDA'].includes(movement)) next.movement = 'Selecciona ENTRADA o SALIDA.'
    setErrors(next)
    if (Object.keys(next).length) return
    setConfirming(true)
  }

  function confirm() {
    focusAfterConfirm.current = true
    start({
      id_persona: person.id_persona,
      id_punto_acceso: point.id_punto_acceso,
      tipo_movimiento: movement,
    })
  }

  function newDeclaration() {
    focusAfterConfirm.current = false
    focusedOperation.current = null
    clear()
    setPerson(null)
    setPoint(null)
    setMovement('')
    setErrors({})
    setConfirming(false)
  }

  function retryDeclaration() {
    focusAfterConfirm.current = true
    focusedOperation.current = null
    retry()
  }

  const event = submission?.response?.data
  const successful = submission?.phase === 'success'
  const replay = submission?.response?.status === 200

  return <section className="page-section" aria-labelledby="manual-access-title">
    <div className="page-head"><div><p className="eyebrow">Accesos manuales</p>
      <h1 id="manual-access-title">Registrar entrada o salida</h1>
      <p className="page-intro">Registra un movimiento declarado. El resultado funcional no confirma presencia real ni acciona puertas.</p>
    </div></div>

    <div className="access-stack">
      <EligiblePersonSelector selected={person} onSelect={selectPerson} disabled={locked} error={errors.person} />
      <ActivePointSelector selected={point} onSelect={selectPoint} disabled={locked} error={errors.point} />
      <section className="form-panel" aria-labelledby="movement-title">
        <h2 id="movement-title">Movimiento declarado</h2>
        <SelectField id="tipo_movimiento_manual" label="Tipo de movimiento" required
          value={movement} disabled={locked} error={errors.movement}
          onChange={(e) => { setMovement(e.target.value); setErrors((current) => ({ ...current, movement: '' })) }}>
          <option value="">Selecciona un movimiento</option>
          <option value="ENTRADA">ENTRADA</option>
          <option value="SALIDA">SALIDA</option>
        </SelectField>
        {!locked && <button ref={confirmTrigger} type="button" className="btn btn-primary"
          disabled={confirming} onClick={prepare}>Revisar declaración</button>}
        {confirming && !locked && <Confirmation title="Confirmar movimiento manual"
          description={`Declarar ${movement} de ${person?.nombre} en ${point?.codigo} · ${point?.nombre}. El servidor validará nuevamente la Persona y el Punto.`}
          confirmLabel="Confirmar registro" triggerRef={confirmTrigger}
          onCancel={() => setConfirming(false)} onConfirm={confirm} />}
      </section>
    </div>

    {submission && <section ref={outcomePanel} tabIndex={-1} aria-live="polite"
      aria-labelledby={successful ? 'access-result-title'
        : submission.phase === 'sending' ? 'access-sending-title' : 'access-problem-title'}
      className={`${successful ? 'detail-panel' : 'form-panel'} access-outcome`}>
      {submission.phase === 'sending' && <>
        <h2 id="access-sending-title">Enviando declaración</h2>
        <p>No cierres ni repitas la operación.</p>
      </>}
      {successful && <>
        <h2 id="access-result-title">{replay ? 'Declaración ya registrada' : 'Declaración registrada'}</h2>
        <p>{replay ? 'La misma declaración se recuperó sin crear otro evento.' : 'Flask confirmó una declaración nueva.'}</p>
        <DetailGrid items={[
          { label: 'Movimiento', value: event.tipo_movimiento },
          { label: 'Resultado', value: event.resultado },
          { label: 'Método', value: event.metodo_registro },
          { label: 'Instante en Bogotá', value: formatBogota(event.fecha_hora_ocurrencia) },
          ...(canManagePeople(user) ? [{ label: 'ID del evento', value: event.id_evento_acceso }] : []),
        ]} />
        {event.tipo_incidencia_secuencia && <Alert tone="warning"
          message={`Se registró una incidencia de secuencia: ${INCIDENCE_LABELS[event.tipo_incidencia_secuencia] || event.tipo_incidencia_secuencia}. No equivale a una denegación automática.`} />}
        {canManagePeople(user) && event.tipo_incidencia_secuencia &&
          <Link className="btn btn-outline-secondary mt-3"
            to={`/eventos-acceso/incidencias/${event.id_evento_acceso}`}>Consultar incidencia</Link>}
        <button type="button" className="btn btn-primary mt-3 ms-2" onClick={newDeclaration}>
          Registrar otra declaración
        </button>
      </>}
      {['uncertain', 'preflight', 'rejected', 'conflict', 'localError'].includes(submission.phase) && <>
        <h2 id="access-problem-title">No se confirmó el registro</h2>
        <Alert tone={submission.phase === 'uncertain' ? 'warning' : 'danger'} message={submission.error} />
        {['uncertain', 'preflight'].includes(submission.phase) && <button type="button"
          className="btn btn-primary" onClick={retryDeclaration}>Reintentar la misma declaración</button>}
        {submission.phase === 'uncertain' && <p className="muted mt-3">
          Si el resultado sigue desconocido, consulta con un administrador antes de declarar otro movimiento.
        </p>}
        {['rejected', 'conflict', 'localError'].includes(submission.phase) &&
          <button type="button" className="btn btn-outline-secondary" onClick={newDeclaration}>
            {submission.phase === 'rejected' ? 'Revisar formulario' : 'Cerrar esta solicitud y empezar otra'}
          </button>}
      </>}
    </section>}

    <p className="muted access-recovery-note">
      Si recargaste o cerraste la página tras un resultado incierto, la clave en memoria no puede recuperarse.
      Antes de registrar de nuevo el mismo movimiento, solicita a un administrador que revise el caso.
    </p>
  </section>
}
