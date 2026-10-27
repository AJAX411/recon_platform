import { useContext } from 'react'
import { AuthContext } from './context.js'

export function useAuth() { return useContext(AuthContext) }
export const canManagePeople = (user) => ['SUPERADMIN', 'ADMINISTRADOR'].includes(user?.rol)
export const canManageUsers = (user) => user?.rol === 'SUPERADMIN'
export const canEditResources = (user) => ['SUPERADMIN', 'ADMINISTRADOR'].includes(user?.rol)
export const canInspectAccesses = (user) => ['SUPERADMIN', 'ADMINISTRADOR'].includes(user?.rol)
