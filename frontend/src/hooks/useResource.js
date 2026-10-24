import { useEffect, useState } from 'react'
import { useAuth } from '../auth/useAuth.js'

export function useResource(load, id) {
  const { expire } = useAuth()
  const [resource, setResource] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    if (!/^[1-9]\d*$/.test(id)) {
      setStatus('error')
      setError('El identificador no es válido.')
      return
    }
    const controller = new AbortController()
    setStatus('loading')
    setError('')
    load(id, controller.signal)
      .then((data) => { if (!controller.signal.aborted) { setResource(data); setStatus('success') } })
      .catch((failure) => {
        if (controller.signal.aborted) return
        if (failure.status === 401) expire()
        else { setError(failure.message); setStatus('error') }
      })
    return () => controller.abort()
  }, [load, id, revision, expire])

  return { resource, setResource, status, error, retry: () => setRevision((value) => value + 1) }
}
