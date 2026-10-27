import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { useAuth, canEditResources, canInspectAccesses, canManagePeople, canManageUsers } from './auth/useAuth.js'
import { PendingManualProvider } from './access/PendingManualProvider.jsx'
import { usePendingManual } from './access/usePendingManual.js'
import { Alert, Skeleton } from './components/Feedback.jsx'
import { LoginPage } from './pages/LoginPage.jsx'
import { PeopleListPage } from './pages/PeopleListPage.jsx'
import { PersonDetailPage } from './pages/PersonDetailPage.jsx'
import { PersonCreatePage } from './pages/PersonCreatePage.jsx'
import { UsersListPage } from './pages/UsersListPage.jsx'
import { UserCreatePage } from './pages/UserCreatePage.jsx'
import { UserDetailPage } from './pages/UserDetailPage.jsx'
import { PointsListPage } from './pages/PointsListPage.jsx'
import { PointCreatePage } from './pages/PointCreatePage.jsx'
import { PointDetailPage } from './pages/PointDetailPage.jsx'
import { DevicesListPage } from './pages/DevicesListPage.jsx'
import { DeviceCreatePage } from './pages/DeviceCreatePage.jsx'
import { DeviceDetailPage } from './pages/DeviceDetailPage.jsx'
import { AccessManualPage } from './pages/AccessManualPage.jsx'
import { AccessHistoryPage } from './pages/AccessHistoryPage.jsx'
import { AccessAlertsPage } from './pages/AccessAlertsPage.jsx'
import { AccessIncidentPage } from './pages/AccessIncidentPage.jsx'

function RouteFocus() {
  const { pathname } = useLocation()
  const previousPath = useRef(pathname)
  useEffect(() => {
    const page = pathname === '/login' ? 'Iniciar sesión'
      : pathname === '/personas/nueva' ? 'Registrar Persona'
        : pathname === '/personas' ? 'Personas'
          : pathname.startsWith('/personas/') ? 'Consultar Persona'
            : pathname === '/usuarios/nuevo' ? 'Crear cuenta'
              : pathname === '/usuarios' ? 'Usuarios'
                : pathname.startsWith('/usuarios/') ? 'Consultar cuenta'
                  : pathname === '/puntos-acceso/nuevo' ? 'Crear Punto de Acceso'
                    : pathname === '/puntos-acceso' ? 'Puntos de Acceso'
                      : pathname.startsWith('/puntos-acceso/') ? 'Consultar Punto de Acceso'
                        : pathname === '/dispositivos-edge/nuevo' ? 'Registrar dispositivo'
                          : pathname === '/dispositivos-edge' ? 'Dispositivos Edge'
                        : pathname.startsWith('/dispositivos-edge/') ? 'Consultar dispositivo'
                          : pathname === '/eventos-acceso/manual' ? 'Registro manual de acceso'
                            : pathname === '/eventos-acceso/historial' ? 'Historial de accesos'
                              : pathname === '/eventos-acceso/alertas' ? 'Alertas de acceso'
                                : pathname.startsWith('/eventos-acceso/incidencias/') ? 'Detalle de incidencia' : 'Inicio'
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
  const { submission } = usePendingManual()
  const navigate = useNavigate()
  const [logoutError, setLogoutError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleLogout() {
    if (submission && ['sending', 'uncertain', 'preflight', 'conflict'].includes(submission.phase)
      && !window.confirm('Hay una declaración manual sin resolver. Al cerrar sesión perderás su clave de reintento. Consulta con un administrador si el resultado sigue incierto. ¿Cerrar sesión?')) return
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
        {canManageUsers(user) && <NavLink to="/usuarios" className={({ isActive }) => `side-link${isActive ? ' active' : ''}`}>Usuarios</NavLink>}
        <NavLink to="/puntos-acceso" className={({ isActive }) => `side-link${isActive ? ' active' : ''}`}>Puntos de Acceso</NavLink>
        <NavLink to="/dispositivos-edge" className={({ isActive }) => `side-link${isActive ? ' active' : ''}`}>Dispositivos Edge</NavLink>
        <NavLink to="/eventos-acceso/manual" className={({ isActive }) => `side-link${isActive ? ' active' : ''}`}>Registro manual</NavLink>
        <NavLink to="/eventos-acceso/historial" className={({ isActive }) => `side-link${isActive ? ' active' : ''}`}>Historial de accesos</NavLink>
        <NavLink to="/eventos-acceso/alertas" className={({ isActive }) => `side-link${isActive ? ' active' : ''}`}>Alertas</NavLink>
      </nav>
      <main id="contenido" tabIndex={-1} className="main-content">
        <Alert message={logoutError} />
        {submission && ['sending', 'uncertain', 'preflight', 'conflict'].includes(submission.phase)
          && <div className="alert alert-warning" role="status">
            Hay una declaración manual pendiente en esta sesión. <NavLink to="/eventos-acceso/manual">Revisar declaración</NavLink>.
          </div>}
        {children}
      </main>
    </div>
  </div>
}

function HomePage() {
  const { user } = useAuth()
  return <section className="page-section" aria-labelledby="inicio-title">
    <div className="eyebrow">Plataforma administrativa</div>
    <h1 id="inicio-title">Bienvenido a Recon Facial</h1>
    <p className="page-intro">Sesión activa como <strong>{user.rol}</strong>. Selecciona una opción disponible para tu rol.</p>
    <div className="home-features">
      {canManagePeople(user) && <div className="feature-panel"><div><h2>Personas</h2><p>Consulta y registro administrativo.</p></div>
        <NavLink className="btn btn-primary" to="/personas">Ver Personas</NavLink></div>}
      {canManageUsers(user) && <div className="feature-panel"><div><h2>Usuarios</h2><p>Administración de cuentas y roles.</p></div>
        <NavLink className="btn btn-primary" to="/usuarios">Ver Usuarios</NavLink></div>}
      <div className="feature-panel"><div><h2>Puntos de Acceso</h2><p>Consulta de ubicaciones administrativas.</p></div>
        <NavLink className="btn btn-primary" to="/puntos-acceso">Ver Puntos</NavLink></div>
      <div className="feature-panel"><div><h2>Dispositivos Edge</h2><p>Consulta administrativa de dispositivos.</p></div>
        <NavLink className="btn btn-primary" to="/dispositivos-edge">Ver Dispositivos</NavLink></div>
      <div className="feature-panel"><div><h2>Accesos manuales</h2><p>Registro de movimientos y consulta autorizada.</p></div>
        <NavLink className="btn btn-primary" to="/eventos-acceso/manual">Registrar movimiento</NavLink></div>
    </div>
  </section>
}

function Protected({ children, peopleOnly = false, superOnly = false, resourceEditOnly = false,
  accessAdminOnly = false }) {
  const { user, status, error, refresh } = useAuth()
  if (status === 'loading') return <main id="contenido" tabIndex={-1} className="centered-state"><Skeleton rows={3} /></main>
  if (status === 'error') return <main id="contenido" tabIndex={-1} className="centered-state"><Alert message={error} onRetry={refresh} /></main>
  if (!user) return <Navigate to="/login" replace />
  if (peopleOnly && !canManagePeople(user)) return <Navigate to="/" replace />
  if (superOnly && !canManageUsers(user)) return <Navigate to="/" replace />
  if (resourceEditOnly && !canEditResources(user)) return <Navigate to="/" replace />
  if (accessAdminOnly && !canInspectAccesses(user)) return <Navigate to="/" replace />
  return <AppLayout key={`${user.id_usuario}:${user.rol}`}>{children}</AppLayout>
}

function AppContent() {
  const { user, status } = useAuth()
  return <><SkipLink /><Routes>
    <Route path="/login" element={status === 'authenticated' && user ? <Navigate to="/" replace /> : <LoginPage />} />
    <Route path="/" element={<Protected><HomePage /></Protected>} />
    <Route path="/personas" element={<Protected peopleOnly><PeopleListPage /></Protected>} />
    <Route path="/personas/nueva" element={<Protected peopleOnly><PersonCreatePage /></Protected>} />
    <Route path="/personas/:id" element={<Protected peopleOnly><PersonDetailPage /></Protected>} />
    <Route path="/usuarios" element={<Protected superOnly><UsersListPage /></Protected>} />
    <Route path="/usuarios/nuevo" element={<Protected superOnly><UserCreatePage /></Protected>} />
    <Route path="/usuarios/:id" element={<Protected superOnly><UserDetailPage /></Protected>} />
    <Route path="/puntos-acceso" element={<Protected><PointsListPage /></Protected>} />
    <Route path="/puntos-acceso/nuevo" element={<Protected resourceEditOnly><PointCreatePage /></Protected>} />
    <Route path="/puntos-acceso/:id" element={<Protected><PointDetailPage /></Protected>} />
    <Route path="/dispositivos-edge" element={<Protected><DevicesListPage /></Protected>} />
    <Route path="/dispositivos-edge/nuevo" element={<Protected resourceEditOnly><DeviceCreatePage /></Protected>} />
    <Route path="/dispositivos-edge/:id" element={<Protected><DeviceDetailPage /></Protected>} />
    <Route path="/eventos-acceso/manual" element={<Protected><AccessManualPage /></Protected>} />
    <Route path="/eventos-acceso/historial" element={<Protected><AccessHistoryPage /></Protected>} />
    <Route path="/eventos-acceso/alertas" element={<Protected><AccessAlertsPage /></Protected>} />
    <Route path="/eventos-acceso/incidencias/:id" element={<Protected accessAdminOnly><AccessIncidentPage /></Protected>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes><RouteFocus /></>
}

export function App() {
  return <PendingManualProvider><AppContent /></PendingManualProvider>
}
