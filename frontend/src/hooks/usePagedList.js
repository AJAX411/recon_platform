import { useEffect, useState } from 'react'
import { useAuth } from '../auth/useAuth.js'

export const PAGE_SIZE = 20

export function usePagedList(load, collectionKey, initialFilters = {}) {
  const { expire } = useAuth()
  const [draft, setDraft] = useState(initialFilters)
  const [filters, setFilters] = useState(initialFilters)
  const [offset, setOffset] = useState(0)
  const [rows, setRows] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setStatus('loading')
    setError('')
    load(filters, offset, PAGE_SIZE, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return
        setRows(response[collectionKey])
        setStatus('success')
      })
      .catch((failure) => {
        if (controller.signal.aborted) return
        if (failure.status === 401) expire()
        else { setError(failure.message); setStatus('error') }
      })
    return () => controller.abort()
  }, [load, collectionKey, filters, offset, revision, expire])

  function apply(event) {
    event.preventDefault()
    setOffset(0)
    setFilters(Object.fromEntries(Object.entries(draft).map(([key, value]) => [key, String(value).trim()])))
    setRevision((value) => value + 1)
  }

  function clear() {
    setDraft(initialFilters)
    setFilters(initialFilters)
    setOffset(0)
    setRevision((value) => value + 1)
  }

  return {
    draft, setDraft, filters, rows, status, error, offset, apply, clear,
    retry: () => setRevision((value) => value + 1),
    previous: () => setOffset((value) => Math.max(0, value - PAGE_SIZE)),
    next: () => setOffset((value) => Math.min(1_000_000, value + PAGE_SIZE)),
  }
}
