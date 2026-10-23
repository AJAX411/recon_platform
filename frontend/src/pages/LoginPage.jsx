import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth.js'
import { Alert, Skeleton } from '../components/Feedback.jsx'
import { Field } from '../components/Field.jsx'

export function LoginPage() {
  const { status, error: sessionError, refresh, signIn } = useAuth()
  const navigate = useNavigate()
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setPending(true)
    setError('')
    try { await signIn(login.trim(), password); navigate('/', { replace: true }) }
    catch (failure) { setError(failure.message) }
    finally { setPending(false); setPassword('') }
  }

  return <main id="contenido" tabIndex={-1} className="login-page">
    <section className="login-aside" aria-label="Identidad del proyecto">
      <span className="brand-mark large" aria-hidden="true">R</span>
      <p className="eyebrow light">Proyecto Recon Facial</p>
      <h1>Plataforma de administración</h1>
      <p>Acceso para usuarios autorizados de la plataforma.</p>
    </section>
    <section className="login-panel" aria-labelledby="login-title">
      <div className="login-card">
        <p className="eyebrow">Acceso seguro</p>
        <h2 id="login-title">Iniciar sesión</h2>
        <p className="muted">Ingresa con tu cuenta de plataforma.</p>
        {status === 'loading' ? <Skeleton rows={3} /> : status === 'error' ? <Alert message={sessionError} onRetry={refresh} /> : <>
          <Alert message={error} />
          <form onSubmit={handleSubmit}>
            <Field id="login" label="Usuario" autoComplete="username" required maxLength={100}
              value={login} onChange={(event) => setLogin(event.target.value)} />
            <Field id="contrasena" label="Contraseña" type="password" autoComplete="current-password" required
              value={password} onChange={(event) => setPassword(event.target.value)} />
            <button className="btn btn-primary w-100" type="submit" disabled={pending}>{pending ? 'Ingresando…' : 'Ingresar'}</button>
          </form>
        </>}
      </div>
    </section>
  </main>
}
