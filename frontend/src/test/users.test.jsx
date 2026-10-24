import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../auth/AuthContext.jsx'
import { UsersListPage } from '../pages/UsersListPage.jsx'
import { UserCreatePage } from '../pages/UserCreatePage.jsx'
import { UserDetailPage } from '../pages/UserDetailPage.jsx'

vi.mock('../api/auth.js', () => ({ getCurrentUser: vi.fn(), login: vi.fn(), logout: vi.fn() }))
vi.mock('../api/usuarios.js', () => ({
  listUsers: vi.fn(), getUser: vi.fn(), getRoles: vi.fn(), createUser: vi.fn(),
  changeUserRole: vi.fn(), changeUserState: vi.fn(),
}))

import { getCurrentUser } from '../api/auth.js'
import { listUsers, getUser, getRoles, createUser, changeUserRole, changeUserState } from '../api/usuarios.js'

const roles = { roles: [
  { nombre: 'SUPERADMIN', asignable: false }, { nombre: 'ADMINISTRADOR', asignable: true },
  { nombre: 'OPERADOR', asignable: true },
] }

function renderUsers(path) {
  return render(<MemoryRouter initialEntries={[path]}><AuthProvider><Routes>
    <Route path="/usuarios" element={<UsersListPage />} />
    <Route path="/usuarios/nuevo" element={<UserCreatePage />} />
    <Route path="/usuarios/:id" element={<UserDetailPage />} />
  </Routes></AuthProvider></MemoryRouter>)
}

describe('administración de Usuarios con datos ficticios', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getCurrentUser.mockResolvedValue({ id_usuario: 1, login: 'admin.prueba', rol: 'SUPERADMIN' })
    getRoles.mockResolvedValue(roles)
  })

  it('lista y pagina sin inventar un total', async () => {
    const firstPage = Array.from({ length: 20 }, (_, index) => ({
      id_usuario: index + 2, login: `cuenta.prueba${index}`, rol: 'OPERADOR', estado: 'ACTIVO',
    }))
    listUsers.mockResolvedValueOnce({ usuarios: firstPage, limite: 20, desplazamiento: 0 })
      .mockResolvedValueOnce({ usuarios: [], limite: 20, desplazamiento: 20 })
      .mockResolvedValueOnce({ usuarios: firstPage, limite: 20, desplazamiento: 0 })
    renderUsers('/usuarios')
    expect(await screen.findByRole('rowheader', { name: /cuenta.prueba0/ })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByText('No hay cuentas en esta página.')).toBeInTheDocument()
    expect(listUsers).toHaveBeenLastCalledWith({}, 20, 20, expect.any(AbortSignal))
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Anterior' }))
    expect(await screen.findByRole('rowheader', { name: /cuenta.prueba0/ })).toBeInTheDocument()
    expect(listUsers).toHaveBeenLastCalledWith({}, 0, 20, expect.any(AbortSignal))
  })

  it('obtiene los roles y no ofrece SUPERADMIN al crear', async () => {
    createUser.mockResolvedValue({ id_usuario: 9, login: 'nueva.prueba', rol: 'OPERADOR', estado: 'ACTIVO' })
    getUser.mockResolvedValue({ id_usuario: 9, login: 'nueva.prueba', rol: 'OPERADOR', estado: 'ACTIVO' })
    renderUsers('/usuarios/nuevo')
    await screen.findByRole('option', { name: 'OPERADOR' })
    expect(screen.queryByRole('option', { name: 'SUPERADMIN' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))
    expect(screen.getByText(/entre 3 y 64 caracteres/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Usuario *'), { target: { value: 'nueva.prueba' } })
    fireEvent.change(screen.getByLabelText('Rol *'), { target: { value: 'OPERADOR' } })
    fireEvent.change(screen.getByLabelText('Contraseña inicial *'), { target: { value: 'Clave-Ficticia-0007' } })
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))
    await waitFor(() => expect(createUser).toHaveBeenCalledWith({
      login: 'nueva.prueba', contrasena: 'Clave-Ficticia-0007', rol: 'OPERADOR',
    }))
    expect(await screen.findByRole('heading', { name: 'nueva.prueba' })).toBeInTheDocument()
  })

  it('oculta cambios de rol y estado de la cuenta SUPERADMIN protegida', async () => {
    getUser.mockResolvedValue({ id_usuario: 1, login: 'admin.prueba', rol: 'SUPERADMIN', estado: 'ACTIVO' })
    renderUsers('/usuarios/1')
    expect(await screen.findByText(/cuenta SUPERADMIN inicial está protegida/)).toBeInTheDocument()
    const heading = screen.getByRole('heading', { name: 'Datos de la cuenta' })
    expect(within(heading.parentElement).getByText('ACTIVO')).toHaveClass('status-pill')
    expect(document.querySelectorAll('.status-pill')).toHaveLength(1)
    expect(screen.queryByRole('button', { name: 'Guardar rol' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Desactivar cuenta' })).not.toBeInTheDocument()
    expect(getRoles).not.toHaveBeenCalled()
  })

  it('cambia rol y estado solo de una cuenta administrable', async () => {
    getUser.mockResolvedValue({ id_usuario: 9, login: 'nueva.prueba', rol: 'OPERADOR', estado: 'ACTIVO' })
    changeUserRole.mockResolvedValue({ id_usuario: 9, login: 'nueva.prueba', rol: 'ADMINISTRADOR', estado: 'ACTIVO' })
    changeUserState.mockResolvedValue({ id_usuario: 9, login: 'nueva.prueba', rol: 'ADMINISTRADOR', estado: 'INACTIVO' })
    renderUsers('/usuarios/9')
    await screen.findByRole('button', { name: 'Guardar rol' })
    await userEvent.click(screen.getByRole('button', { name: 'Guardar rol' }))
    expect(changeUserRole).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Confirmar cambio de rol' })).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Rol asignable'), 'ADMINISTRADOR')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar rol' }))
    const roleSection = screen.getByRole('heading', { name: 'Rol' }).closest('.form-panel')
    expect(within(roleSection).getByRole('group', { name: /Cambiar el rol de la cuenta/ })).toHaveTextContent('Rol actual: OPERADOR. Rol propuesto: ADMINISTRADOR.')
    expect(screen.getByRole('button', { name: 'Desactivar cuenta' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus()
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(changeUserRole).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Guardar rol' })).toHaveFocus())
    await userEvent.click(screen.getByRole('button', { name: 'Guardar rol' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar cambio de rol' }))
    await waitFor(() => expect(changeUserRole).toHaveBeenCalledWith('9', 'ADMINISTRADOR'))
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar cuenta' }))
    expect(screen.getByText('La desactivación revoca las sesiones vigentes de esta cuenta.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus()
    await userEvent.keyboard('{Enter}')
    expect(changeUserState).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Desactivar cuenta' })).toHaveFocus())
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar cuenta' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar cambio de estado' }))
    await waitFor(() => expect(changeUserState).toHaveBeenCalledWith('9', 'INACTIVO'))
    expect(await screen.findByRole('button', { name: 'Activar cuenta' })).toBeInTheDocument()
  })

  it('muestra 404 al consultar una cuenta ausente', async () => {
    getUser.mockRejectedValue({ status: 404, message: 'La cuenta no existe.' })
    renderUsers('/usuarios/99')
    expect(await screen.findByRole('alert')).toHaveTextContent('La cuenta no existe.')
  })

  it('comunica la duplicidad 409 sin conservar la contraseña en el formulario', async () => {
    createUser.mockRejectedValue({ status: 409, message: 'El identificador de login ya existe.' })
    renderUsers('/usuarios/nuevo')
    await screen.findByRole('option', { name: 'OPERADOR' })
    fireEvent.change(screen.getByLabelText('Usuario *'), { target: { value: 'duplicada.prueba' } })
    fireEvent.change(screen.getByLabelText('Rol *'), { target: { value: 'OPERADOR' } })
    fireEvent.change(screen.getByLabelText('Contraseña inicial *'), { target: { value: 'Clave-Ficticia-0007' } })
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('El identificador de login ya existe.')
    expect(screen.getByLabelText('Contraseña inicial *')).toHaveValue('')
  })
})
