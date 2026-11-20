/** Permisos de navegación por rol para experiencia de usuario; la autorización efectiva permanece en Flask. */
export const ROLES = ['SUPERADMIN', 'ADMINISTRADOR', 'OPERADOR']
export const administrative = (user) => ['SUPERADMIN', 'ADMINISTRADOR'].includes(user?.rol)
export const superadmin = (user) => user?.rol === 'SUPERADMIN'
export function allows(user, permission = 'all') {
  if (!ROLES.includes(user?.rol)) return false
  return permission === 'super' ? superadmin(user) : permission === 'admin' ? administrative(user) : true
}
