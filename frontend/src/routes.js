const route = (path, title, page, permission = 'all', extra = {}) => ({ path, title, page, permission, ...extra })
export const routes = [
  route('/login', 'Iniciar sesión', 'login', 'public'),
  route('/', 'Inicio', 'dashboard'),
  route('/personas', 'Personas', 'list', 'admin', { resource: 'people' }),
  route('/personas/nueva', 'Registrar Persona', 'personCreate', 'admin'),
  route('/personas/:id/editar', 'Editar Persona', 'personEdit', 'admin'),
  route('/personas/:id', 'Consultar Persona', 'detail', 'admin', { resource: 'people' }),
  route('/usuarios', 'Usuarios', 'list', 'super', { resource: 'users' }),
  route('/usuarios/nuevo', 'Crear cuenta', 'create', 'super', { resource: 'users' }),
  route('/usuarios/:id', 'Consultar cuenta', 'detail', 'super', { resource: 'users' }),
  route('/puntos-acceso', 'Puntos de Acceso', 'list', 'all', { resource: 'points' }),
  route('/puntos-acceso/nuevo', 'Crear Punto de Acceso', 'create', 'admin', { resource: 'points' }),
  route('/puntos-acceso/:id', 'Consultar Punto', 'detail', 'all', { resource: 'points' }),
  route('/dispositivos-edge', 'Dispositivos Edge', 'list', 'all', { resource: 'devices' }),
  route('/dispositivos-edge/nuevo', 'Registrar dispositivo', 'create', 'admin', { resource: 'devices' }),
  route('/dispositivos-edge/:id', 'Consultar dispositivo', 'detail', 'all', { resource: 'devices' }),
  route('/eventos-acceso/manual', 'Registro manual', 'manual'),
  route('/eventos-acceso/historial', 'Historial de accesos', 'events'),
  route('/eventos-acceso/alertas', 'Alertas e incidencias', 'alerts'),
  route('/eventos-acceso/incidencias/:id', 'Detalle de incidencia', 'incident', 'admin'),
]
export function matchRoute(path) {
  for (const entry of routes) {
    const names = []
    const pattern = entry.path.split('/').map((part) => {
      if (part.startsWith(':')) { names.push(part.slice(1)); return '([^/]+)' }
      return part
    }).join('/')
    const match = new RegExp('^' + pattern + '$').exec(path)
    if (match) return { ...entry, params: Object.fromEntries(names.map((name, i) => [name, match[i + 1]])) }
  }
  return { path, title: 'Página no encontrada', page: 'notFound', params: {}, permission: 'public' }
}
