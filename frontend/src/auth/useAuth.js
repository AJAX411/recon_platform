import { useContext } from 'react'
import { AuthContext } from './context.js'

export function useAuth() { return useContext(AuthContext) }
export const canManagePeople = (user) => ['SUPERADMIN', 'ADMINISTRADOR'].includes(user?.rol)
