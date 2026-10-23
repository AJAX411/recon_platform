import { useCallback, useEffect, useState } from 'react'
import { ApiError, clearCsrf } from '../api/http.js'
import { getCurrentUser, login as apiLogin, logout as apiLogout } from '../api/auth.js'
import { AuthContext } from './context.js'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setStatus('loading')
    setError('')
    try {
      setUser(await getCurrentUser())
      setStatus('authenticated')
    } catch (failure) {
      setUser(null)
      if (failure instanceof ApiError && failure.status === 401) setStatus('anonymous')
      else { setStatus('error'); setError(failure.message) }
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  async function signIn(username, password) {
    const identity = await apiLogin(username, password)
    setUser(identity)
    setStatus('authenticated')
  }

  async function signOut() {
    try { await apiLogout() }
    catch (failure) {
      if (!(failure instanceof ApiError) || failure.status !== 401) throw failure
      clearCsrf()
    }
    setUser(null)
    setStatus('anonymous')
  }

  const expire = useCallback(() => { clearCsrf(); setUser(null); setStatus('anonymous') }, [])

  return <AuthContext.Provider value={{ user, status, error, refresh, signIn, signOut, expire }}>
    {children}
  </AuthContext.Provider>
}
