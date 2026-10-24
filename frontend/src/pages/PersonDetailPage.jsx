import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getPerson } from '../api/personas.js'
import { useAuth } from '../auth/useAuth.js'
import { Alert, Skeleton } from '../components/Feedback.jsx'
import { StatusBadge } from '../components/StatusBadge.jsx'

function Datum({ label, children }) { return <div><dt>{label}</dt><dd>{children || 'No registrado'}</dd></div> }

export function PersonDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const { expire } = useAuth()
  const [person, setPerson] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)

  useEffect(() => {
    if (!/^[1-9]\d*$/.test(id)) { setError('El identificador de Persona no es válido.'); setStatus('error'); return }
    const controller = new AbortController()
    setStatus('loading')
    getPerson(id, controller.signal).then((data) => { setPerson(data); setStatus('success') })
      .catch((failure) => {
        if (controller.signal.aborted) return
        if (failure.status === 401) expire()
        else { setError(failure.message); setStatus('error') }
      })
    return () => controller.abort()
  }, [id, reload, expire])

  return <section className="page-section" aria-labelledby="person-title">
    <Link className="back-link" to="/personas">← Volver a Personas</Link>
    {status === 'loading' && <Skeleton rows={6} />}
    {status === 'error' && <Alert message={error} onRetry={() => setReload((number) => number + 1)} />}
    {status === 'success' && person && <>
      {location.state?.created && <Alert message="Persona registrada correctamente." tone="success" />}
      <div className="page-head"><div><p className="eyebrow">Persona · ID {person.id_persona}</p>
        <h1 id="person-title">{[person.primer_nombre, person.segundo_nombre, person.primer_apellido, person.segundo_apellido].filter(Boolean).join(' ')}</h1></div>
      </div>
      <div className="detail-panel"><div className="detail-heading"><h2>Información administrativa</h2><StatusBadge estado={person.estado} /></div>
        <dl className="detail-grid">
          <Datum label="Primer nombre">{person.primer_nombre}</Datum><Datum label="Segundo nombre">{person.segundo_nombre}</Datum>
          <Datum label="Primer apellido">{person.primer_apellido}</Datum><Datum label="Segundo apellido">{person.segundo_apellido}</Datum>
          <Datum label="Tipo de Persona">{person.tipo_persona}</Datum><Datum label="Tipo de documento">{person.tipo_documento}</Datum>
          <Datum label="Número de documento">{person.numero_documento}</Datum><Datum label="Identificador institucional">{person.identificador_institucional}</Datum>
        </dl>
      </div>
    </>}
  </section>
}
