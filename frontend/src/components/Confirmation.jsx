import { useEffect, useId, useRef, useState } from 'react'

export function Confirmation({ title, description, confirmLabel, triggerRef, onCancel, onConfirm }) {
  const titleId = useId()
  const descriptionId = useId()
  const cancelRef = useRef(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => { cancelRef.current?.focus() }, [])

  function close() {
    onCancel()
    setTimeout(() => triggerRef.current?.focus(), 0)
  }

  async function confirm() {
    setSubmitting(true)
    try { await onConfirm() }
    finally { close() }
  }

  return <section className="confirmation-panel" role="group" aria-labelledby={titleId} aria-describedby={descriptionId}>
    <h3 id={titleId}>{title}</h3>
    <p id={descriptionId}>{description}</p>
    <div className="form-actions">
      <button ref={cancelRef} className="btn btn-outline-secondary" type="button" disabled={submitting} onClick={close}>Cancelar</button>
      <button className="btn btn-primary" type="button" disabled={submitting} onClick={confirm}>{submitting ? 'Aplicando…' : confirmLabel}</button>
    </div>
  </section>
}
