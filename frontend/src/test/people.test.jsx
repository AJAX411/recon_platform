import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../auth/AuthContext.jsx'
import { PeopleListPage } from '../pages/PeopleListPage.jsx'
import { PersonCreatePage } from '../pages/PersonCreatePage.jsx'

vi.mock('../api/auth.js', () => ({
  getCurrentUser: vi.fn().mockResolvedValue({ id_usuario: 1, login: 'admin.ficticio', rol: 'ADMINISTRADOR' }),
  login: vi.fn(), logout: vi.fn(),
}))
vi.mock('../api/personas.js', () => ({
  listPeople: vi.fn(), getPersonTypes: vi.fn(), createPerson: vi.fn(), getPerson: vi.fn(),
}))

import { listPeople, getPersonTypes, createPerson } from '../api/personas.js'

const types = { tipos: [
  { id_tipo_persona: 1, nombre: 'ESTUDIANTE', estado: 'ACTIVO' },
  { id_tipo_persona: 2, nombre: 'VISITANTE', estado: 'ACTIVO' },
] }

function renderPage(path, element) {
  return render(<MemoryRouter initialEntries={[path]}><AuthProvider><Routes>
    <Route path={path} element={element} />
    <Route path="/personas/:id" element={<p>Persona creada</p>} />
  </Routes></AuthProvider></MemoryRouter>)
}

describe('Personas', () => {
  it('distingue carga y vacío con resultados de la API', async () => {
    let resolveList
    listPeople.mockImplementationOnce(() => new Promise((resolve) => { resolveList = resolve }))
    getPersonTypes.mockResolvedValue(types)
    renderPage('/personas', <PeopleListPage />)
    expect(screen.getByRole('status', { name: 'Cargando información' })).toBeInTheDocument()
    resolveList({ personas: [], limite: 20, desplazamiento: 0 })
    expect(await screen.findByText('No se encontraron Personas con estos filtros.')).toBeInTheDocument()
    expect(listPeople).toHaveBeenCalledWith(expect.any(Object), 0, 20, expect.any(AbortSignal))
  })

  it('muestra una Persona recibida y no inventa resultados', async () => {
    listPeople.mockResolvedValue({ personas: [{ id_persona: 7, primer_nombre: 'Prueba', primer_apellido: 'Ficticia', tipo_documento: 'DOC', numero_documento: 'TEST7', tipo_persona: 'VISITANTE', estado: 'ACTIVO' }], limite: 20, desplazamiento: 0 })
    getPersonTypes.mockResolvedValue(types)
    renderPage('/personas', <PeopleListPage />)
    expect(await screen.findByRole('rowheader', { name: /Prueba Ficticia/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Consultar Prueba Ficticia' })).toHaveAttribute('href', '/personas/7')
  })

  it('muestra errores del servidor en el listado', async () => {
    listPeople.mockRejectedValue({ status: 503, message: 'Servicio no disponible.' })
    getPersonTypes.mockResolvedValue(types)
    renderPage('/personas', <PeopleListPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Servicio no disponible.')
  })

  it('comunica un 403 del backend aunque la sesión indique un rol autorizado', async () => {
    listPeople.mockRejectedValue({ status: 403, message: 'Permiso denegado.' })
    getPersonTypes.mockResolvedValue(types)
    renderPage('/personas', <PeopleListPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Permiso denegado.')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('ofrece reintentar tras un fallo de comunicación en el listado', async () => {
    listPeople.mockRejectedValueOnce({ status: 0, message: 'No se pudo conectar con la plataforma.' })
      .mockResolvedValueOnce({ personas: [], limite: 20, desplazamiento: 0 })
    getPersonTypes.mockResolvedValue(types)
    renderPage('/personas', <PeopleListPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con la plataforma.')
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByText('No se encontraron Personas con estos filtros.')).toBeInTheDocument()
  })

  it('valida estudiante y envía solo los campos del contrato al registrar', async () => {
    getPersonTypes.mockResolvedValue(types)
    createPerson.mockResolvedValue({ id_persona: 8 })
    renderPage('/personas/nueva', <PersonCreatePage />)
    await screen.findByRole('option', { name: 'ESTUDIANTE' })
    fireEvent.change(screen.getByLabelText('Primer nombre *'), { target: { value: 'Prueba' } })
    fireEvent.change(screen.getByLabelText('Primer apellido *'), { target: { value: 'Ficticia' } })
    fireEvent.change(screen.getByLabelText('Tipo de Persona *'), { target: { value: 'ESTUDIANTE' } })
    fireEvent.change(screen.getByLabelText('Tipo de documento *'), { target: { value: 'DOC' } })
    fireEvent.change(screen.getByLabelText('Número de documento *'), { target: { value: 'TEST8' } })
    await userEvent.click(screen.getByRole('button', { name: 'Registrar Persona' }))
    expect(screen.getByText('Obligatorio para ESTUDIANTE.')).toBeInTheDocument()
    expect(createPerson).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText('Identificador institucional *'), { target: { value: 'FIC8' } })
    await userEvent.click(screen.getByRole('button', { name: 'Registrar Persona' }))
    await waitFor(() => expect(screen.getByText('Persona creada')).toBeInTheDocument())
    expect(createPerson).toHaveBeenCalledWith({
      primer_nombre: 'Prueba', segundo_nombre: null, primer_apellido: 'Ficticia', segundo_apellido: null,
      tipo_persona: 'ESTUDIANTE', tipo_documento: 'DOC', numero_documento: 'TEST8', identificador_institucional: 'FIC8',
    })
  })

  it('conserva el formulario y comunica el error de duplicidad del servidor', async () => {
    getPersonTypes.mockResolvedValue(types)
    createPerson.mockRejectedValue({ status: 409, message: 'El identificador de Persona ya existe.' })
    renderPage('/personas/nueva', <PersonCreatePage />)
    await screen.findByRole('option', { name: 'VISITANTE' })
    fireEvent.change(screen.getByLabelText('Primer nombre *'), { target: { value: 'Prueba' } })
    fireEvent.change(screen.getByLabelText('Primer apellido *'), { target: { value: 'Ficticia' } })
    fireEvent.change(screen.getByLabelText('Tipo de Persona *'), { target: { value: 'VISITANTE' } })
    fireEvent.change(screen.getByLabelText('Tipo de documento *'), { target: { value: 'DOC' } })
    fireEvent.change(screen.getByLabelText('Número de documento *'), { target: { value: 'TEST9' } })
    await userEvent.click(screen.getByRole('button', { name: 'Registrar Persona' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('El identificador de Persona ya existe.')
    expect(screen.getByLabelText('Primer nombre *')).toHaveValue('Prueba')
  })

  it('conserva los datos cuando el registro falla con 503', async () => {
    getPersonTypes.mockResolvedValue(types)
    createPerson.mockRejectedValue({ status: 503, message: 'La administración de Personas no está disponible.' })
    renderPage('/personas/nueva', <PersonCreatePage />)
    await screen.findByRole('option', { name: 'VISITANTE' })
    fireEvent.change(screen.getByLabelText('Primer nombre *'), { target: { value: 'Prueba' } })
    fireEvent.change(screen.getByLabelText('Primer apellido *'), { target: { value: 'Ficticia' } })
    fireEvent.change(screen.getByLabelText('Tipo de Persona *'), { target: { value: 'VISITANTE' } })
    fireEvent.change(screen.getByLabelText('Tipo de documento *'), { target: { value: 'DOC' } })
    fireEvent.change(screen.getByLabelText('Número de documento *'), { target: { value: 'TEST10' } })
    await userEvent.click(screen.getByRole('button', { name: 'Registrar Persona' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('La administración de Personas no está disponible.')
    expect(screen.getByLabelText('Número de documento *')).toHaveValue('TEST10')
  })
})
