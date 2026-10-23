import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { useAuth, canManagePeople } from './auth/useAuth.js'
import { Alert, Skeleton } from './components/Feedback.jsx'
import { LoginPage } from './pages/LoginPage.jsx'
import { PeopleListPage } from './pages/PeopleListPage.jsx'
import { PersonDetailPage } from './pages/PersonDetailPage.jsx'
import { PersonCreatePage } from './pages/PersonCreatePage.jsx'

function RouteFocus() {
  const { pathname } = useLocation()
  const previousPath = useRef(pathname)
  useEffect(() => {
    const page = pathname === '/login' ? 'Iniciar sesión'
      : pathname === '/personas/nueva' ? 'Registrar Persona'
        : pathname === '/personas' ? 'Personas'
          : pathname.startsWith('/personas/') ? 'Consultar Persona' : 'Inicio'
    document.title = `${page} · Recon Facial`
    if (previousPath.current !== pathname) document.getElementById('contenido')?.focus()
    previousPath.current = pathname
  }, [pathname])
  return null
}

function SkipLink() {
  function skip(event) {
    event.preventDefault()
    document.getElementById('contenido')?.focus()
  }
  return <a className="skip-link" href="#contenido" onClick={skip}>Saltar al contenido principal</a>
}

function AppLayout({ children }) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [logoutError, setLogoutError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleLogout() {
    setBusy(true)
    setLogoutError('')
    try { await signOut(); navigate('/login', { replace: true }) }
    catch (error) { setLogoutError(error.message) }
    finally { setBusy(false) }
  }

  return <div className="app-shell">
    <header className="topbar">
      <div className="container-fluid topbar-inner">
        <NavLink to="/" className="brand" aria-label="Recon Facial, inicio">
          <span className="brand-mark" aria-hidden="true">R</span>
          <span>Recon <strong>Facial</strong><small>Plataforma administrativa</small></span>
        </NavLink>
        <div className="session-tools">
          <span className="session-identity"><strong>{user.login}</strong><small>{user.rol}</small></span>
          <button type="button" className="btn btn-outline-light btn-sm" onClick={handleLogout} disabled={busy}>
            {busy ? 'Cerrando…' : 'Cerrar sesión'}
          </button>
        </div>
      </div>
    </header>
    <div className="workspace container-fluid">
      <nav className="side-nav" aria-label="Navegación principal">
        <span className="nav-caption">Espacio de trabajo</span>
        <NavLink to="/" end className={({ isActive }) => `side-link${isActive ? ' active' : ''}`}>Inicio</NavLink>
        {canManagePeople(user) && <NavLink to="/personas" className={({ isActive }) => `side-link${isActive ? ' active' : ''}`}>Personas</NavLink>}
      </nav>
      <main id="contenido" tabIndex={-1} className="main-content">
        <Alert message={logoutError} />
        {children}
      </main>
    </div>
  </div>
}

function HomePage() {
  const { user } = useAuth()
  return <section className="page-section" aria-labelledby="inicio-title">
    <div className="eyebrow">Plataforma · Incremento 0007-A</div>
    <h1 id="inicio-title">Bienvenido a Recon Facial</h1>
    <p className="page-intro">Sesión activa como <strong>{user.rol}</strong>. Selecciona una opción disponible para tu rol.</p>
    {canManagePeople(user) ? <div className="feature-panel">
      <div><h2>Administración de Personas</h2><p>Consulta y registra información administrativa de Personas.</p></div>
      <NavLink className="btn btn-primary" to="/personas">Ver Personas</NavLink>
    </div> : <div className="feature-panel"><p className="mb-0">No hay módulos habilitados para tu rol en esta entrega.</p></div>}
  </section>
}

function Protected({ children, peopleOnly = false }) {
  const { user, status, error, refresh } = useAuth()
  if (status === 'loading') return <main id="contenido" tabIndex={-1} className="centered-state"><Skeleton rows={3} /></main>
  if (status === 'error') return <main id="contenido" tabIndex={-1} className="centered-state"><Alert message={error} onRetry={refresh} /></main>
  if (!user) return <Navigate to="/login" replace />
  if (peopleOnly && !canManagePeople(user)) return <Navigate to="/" replace />
  return <AppLayout>{children}</AppLayout>
}

export function App() {
  const { user, status } = useAuth()
  return <><SkipLink /><Routes>
    <Route path="/login" element={status === 'authenticated' && user ? <Navigate to="/" replace /> : <LoginPage />} />
    <Route path="/" element={<Protected><HomePage /></Protected>} />
    <Route path="/personas" element={<Protected peopleOnly><PeopleListPage /></Protected>} />
    <Route path="/personas/nueva" element={<Protected peopleOnly><PersonCreatePage /></Protected>} />
    <Route path="/personas/:id" element={<Protected peopleOnly><PersonDetailPage /></Protected>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes><RouteFocus /></>
}
