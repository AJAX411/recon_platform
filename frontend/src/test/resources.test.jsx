import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../auth/AuthContext.jsx'
import { PointsListPage } from '../pages/PointsListPage.jsx'
import { PointCreatePage } from '../pages/PointCreatePage.jsx'
import { PointDetailPage } from '../pages/PointDetailPage.jsx'
import { DevicesListPage } from '../pages/DevicesListPage.jsx'
import { DeviceCreatePage } from '../pages/DeviceCreatePage.jsx'
import { DeviceDetailPage } from '../pages/DeviceDetailPage.jsx'

vi.mock('../api/auth.js', () => ({ getCurrentUser: vi.fn(), login: vi.fn(), logout: vi.fn() }))
vi.mock('../api/puntos.js', () => ({ listPoints: vi.fn(), getPoint: vi.fn(), createPoint: vi.fn(), editPoint: vi.fn(), changePointState: vi.fn() }))
vi.mock('../api/dispositivos.js', () => ({ listDevices: vi.fn(), getDevice: vi.fn(), createDevice: vi.fn(), editDevice: vi.fn(), changeDeviceState: vi.fn(), changeDeviceMode: vi.fn() }))

import { getCurrentUser } from '../api/auth.js'
import { listPoints, getPoint, createPoint, editPoint, changePointState } from '../api/puntos.js'
import { listDevices, getDevice, createDevice, editDevice, changeDeviceState, changeDeviceMode } from '../api/dispositivos.js'

const point = { id_punto_acceso: 7, codigo: 'P-PRUEBA', nombre: 'Punto ficticio', descripcion: null, estado: 'ACTIVO', fecha_creacion: '2026-10-20T00:00:00', fecha_actualizacion: '2026-10-20T00:00:00' }
const device = { id_dispositivo: 8, id_punto_acceso: 7, codigo: 'D-PRUEBA', nombre: 'Nodo ficticio', modo_operacion: 'ENTRADA', estado: 'INACTIVO', ultima_comunicacion: null, fecha_creacion: '2026-10-20T00:00:00', fecha_actualizacion: '2026-10-20T00:00:00' }

function renderResources(path) {
  return render(<MemoryRouter initialEntries={[path]}><AuthProvider><Routes>
    <Route path="/puntos-acceso" element={<PointsListPage />} />
    <Route path="/puntos-acceso/nuevo" element={<PointCreatePage />} />
    <Route path="/puntos-acceso/:id" element={<PointDetailPage />} />
    <Route path="/dispositivos-edge" element={<DevicesListPage />} />
    <Route path="/dispositivos-edge/nuevo" element={<DeviceCreatePage />} />
    <Route path="/dispositivos-edge/:id" element={<DeviceDetailPage />} />
  </Routes></AuthProvider></MemoryRouter>)
}

describe('Puntos y Dispositivos con datos ficticios', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getCurrentUser.mockResolvedValue({ id_usuario: 2, login: 'admin.prueba', rol: 'ADMINISTRADOR' })
  })

  it('filtra y pagina puntos usando únicamente filtros admitidos', async () => {
    listPoints.mockResolvedValueOnce({ puntos: Array.from({ length: 20 }, (_, index) => ({ ...point, id_punto_acceso: index + 1, codigo: `P${index}` })), limite: 20, desplazamiento: 0 })
      .mockResolvedValueOnce({ puntos: [point], limite: 20, desplazamiento: 20 })
      .mockResolvedValueOnce({ puntos: [point], limite: 20, desplazamiento: 0 })
    renderResources('/puntos-acceso')
    expect(await screen.findByRole('rowheader', { name: /P0/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Aplicar filtros' })).toHaveClass('btn-primary')
    expect(screen.getByRole('button', { name: 'Limpiar' })).toHaveClass('btn-outline-secondary')
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    await waitFor(() => expect(listPoints).toHaveBeenLastCalledWith({ codigo: '', estado: '' }, 20, 20, expect.any(AbortSignal)))
    fireEvent.change(screen.getByLabelText('Código'), { target: { value: 'P-PRUEBA' } })
    fireEvent.change(screen.getByLabelText('Estado'), { target: { value: 'ACTIVO' } })
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' }))
    await waitFor(() => expect(listPoints).toHaveBeenLastCalledWith({ codigo: 'P-PRUEBA', estado: 'ACTIVO' }, 0, 20, expect.any(AbortSignal)))
  })

  it('permite volver desde una segunda página vacía de puntos', async () => {
    const first = Array.from({ length: 20 }, (_, index) => ({ ...point, id_punto_acceso: index + 1, codigo: `P${index}` }))
    listPoints.mockResolvedValueOnce({ puntos: first, limite: 20, desplazamiento: 0 })
      .mockResolvedValueOnce({ puntos: [], limite: 20, desplazamiento: 20 })
      .mockResolvedValueOnce({ puntos: first, limite: 20, desplazamiento: 0 })
    renderResources('/puntos-acceso')
    await screen.findByRole('rowheader', { name: /P0/ })
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByText('No se encontraron Puntos de Acceso con estos filtros.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Anterior' }))
    expect(await screen.findByRole('rowheader', { name: /P0/ })).toBeInTheDocument()
    expect(listPoints).toHaveBeenLastCalledWith({ codigo: '', estado: '' }, 0, 20, expect.any(AbortSignal))
  })

  it('crea un punto con los campos aprobados y comunica 409', async () => {
    createPoint.mockRejectedValueOnce({ status: 409, message: 'El código ya existe.' })
      .mockResolvedValueOnce(point)
    getPoint.mockResolvedValue(point)
    renderResources('/puntos-acceso/nuevo')
    await userEvent.click(screen.getByRole('button', { name: 'Crear Punto de Acceso' }))
    expect(screen.getByText('El código es obligatorio.')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Código *'), { target: { value: 'P-PRUEBA' } })
    fireEvent.change(screen.getByLabelText('Nombre *'), { target: { value: 'Punto ficticio' } })
    await userEvent.click(screen.getByRole('button', { name: 'Crear Punto de Acceso' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('El código ya existe.')
    await userEvent.click(screen.getByRole('button', { name: 'Crear Punto de Acceso' }))
    await waitFor(() => expect(createPoint).toHaveBeenLastCalledWith({ codigo: 'P-PRUEBA', nombre: 'Punto ficticio', descripcion: null }))
    expect(await screen.findByRole('heading', { name: 'Punto ficticio' })).toBeInTheDocument()
  })

  it('permite a OPERADOR cambiar estado de punto pero no editarlo', async () => {
    getCurrentUser.mockResolvedValue({ id_usuario: 3, login: 'operador.prueba', rol: 'OPERADOR' })
    getPoint.mockResolvedValue(point)
    changePointState.mockResolvedValue({ ...point, estado: 'INACTIVO' })
    renderResources('/puntos-acceso/7')
    expect(await screen.findByRole('button', { name: 'Desactivar punto' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Editar punto' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar punto' }))
    expect(screen.getByText(/cambio modifica el estado administrativo/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(changePointState).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar punto' }))
    await userEvent.tab()
    expect(screen.getByRole('button', { name: 'Confirmar cambio de estado' })).toHaveFocus()
    await userEvent.keyboard('{Enter}')
    await waitFor(() => expect(changePointState).toHaveBeenCalledWith('7', 'INACTIVO'))
    expect(await screen.findByRole('button', { name: 'Activar punto' })).toBeInTheDocument()
    expect(editPoint).not.toHaveBeenCalled()
  })

  it('edita solo nombre y descripción de un punto con rol administrador', async () => {
    getPoint.mockResolvedValue(point)
    editPoint.mockResolvedValue({ ...point, nombre: 'Punto actualizado', descripcion: 'Descripción de prueba' })
    renderResources('/puntos-acceso/7')
    await screen.findByRole('heading', { name: 'Editar punto' })
    const heading = screen.getByRole('heading', { name: 'Información administrativa' })
    expect(within(heading.parentElement).getByText('ACTIVO')).toHaveClass('status-pill')
    expect(document.querySelectorAll('.status-pill')).toHaveLength(1)
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    expect(editPoint).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Confirmar edición' })).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Nombre *'), { target: { value: '  Punto ficticio  ' } })
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    expect(editPoint).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Confirmar edición' })).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Nombre *'), { target: { value: 'Punto actualizado' } })
    fireEvent.change(screen.getByLabelText('Descripción'), { target: { value: 'Descripción de prueba' } })
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    const editSection = screen.getByRole('heading', { name: 'Editar punto' }).closest('.form-panel')
    expect(within(editSection).getByRole('group', { name: /Guardar los cambios del punto/ })).toHaveTextContent('Nombre: «Punto ficticio» → «Punto actualizado».')
    expect(within(editSection).getByRole('group', { name: /Guardar los cambios del punto/ })).toHaveTextContent('Descripción: «Sin descripción» → «Descripción de prueba».')
    expect(screen.getByRole('button', { name: 'Desactivar punto' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(editPoint).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Guardar cambios' })).toHaveFocus())
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar edición' }))
    await waitFor(() => expect(editPoint).toHaveBeenCalledWith('7', { nombre: 'Punto actualizado', descripcion: 'Descripción de prueba' }))
  })

  it('muestra 503 de listado y permite reintentar dispositivos', async () => {
    listDevices.mockRejectedValueOnce({ status: 503, message: 'La administración no está disponible.' })
      .mockResolvedValueOnce({ dispositivos: [], limite: 20, desplazamiento: 0 })
    renderResources('/dispositivos-edge')
    expect(await screen.findByRole('alert')).toHaveTextContent('La administración no está disponible.')
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByText('No se encontraron Dispositivos Edge con estos filtros.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
  })

  it('permite volver desde una segunda página vacía de dispositivos', async () => {
    const first = Array.from({ length: 20 }, (_, index) => ({ ...device, id_dispositivo: index + 1, codigo: `D${index}` }))
    listDevices.mockResolvedValueOnce({ dispositivos: first, limite: 20, desplazamiento: 0 })
      .mockResolvedValueOnce({ dispositivos: [], limite: 20, desplazamiento: 20 })
      .mockResolvedValueOnce({ dispositivos: first, limite: 20, desplazamiento: 0 })
    renderResources('/dispositivos-edge')
    await screen.findByRole('rowheader', { name: /D0/ })
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByText('No se encontraron Dispositivos Edge con estos filtros.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Anterior' }))
    expect(await screen.findByRole('rowheader', { name: /D0/ })).toBeInTheDocument()
    expect(listDevices).toHaveBeenLastCalledWith({ codigo: '', estado: '', modo_operacion: '', id_punto_acceso: '' }, 0, 20, expect.any(AbortSignal))
  })

  it('filtra dispositivos por modo y Punto de Acceso', async () => {
    listDevices.mockResolvedValue({ dispositivos: [device], limite: 20, desplazamiento: 0 })
    renderResources('/dispositivos-edge')
    expect(await screen.findByRole('rowheader', { name: /D-PRUEBA/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Aplicar filtros' })).toHaveClass('btn-primary')
    expect(screen.getByRole('button', { name: 'Limpiar' })).toHaveClass('btn-outline-secondary')
    fireEvent.change(screen.getByLabelText('Modo de operación'), { target: { value: 'ENTRADA' } })
    fireEvent.change(screen.getByLabelText('ID del Punto de Acceso'), { target: { value: '7' } })
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' }))
    await waitFor(() => expect(listDevices).toHaveBeenLastCalledWith({ codigo: '', estado: '', modo_operacion: 'ENTRADA', id_punto_acceso: '7' }, 0, 20, expect.any(AbortSignal)))
  })

  it('registra un dispositivo sin inventar estado ni comunicación', async () => {
    createDevice.mockRejectedValueOnce({ status: 400, message: 'Los datos no son válidos.' })
      .mockResolvedValueOnce(device)
    getDevice.mockResolvedValue(device)
    renderResources('/dispositivos-edge/nuevo')
    fireEvent.change(screen.getByLabelText('ID del Punto de Acceso *'), { target: { value: '7' } })
    fireEvent.change(screen.getByLabelText('Código *'), { target: { value: 'D-PRUEBA' } })
    fireEvent.change(screen.getByLabelText('Nombre *'), { target: { value: 'Nodo ficticio' } })
    fireEvent.change(screen.getByLabelText('Modo de operación *'), { target: { value: 'ENTRADA' } })
    await userEvent.click(screen.getByRole('button', { name: 'Registrar dispositivo' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Los datos no son válidos.')
    await userEvent.click(screen.getByRole('button', { name: 'Registrar dispositivo' }))
    await waitFor(() => expect(createDevice).toHaveBeenLastCalledWith({ id_punto_acceso: 7, codigo: 'D-PRUEBA', nombre: 'Nodo ficticio', modo_operacion: 'ENTRADA' }))
    expect(await screen.findByRole('heading', { name: 'Nodo ficticio' })).toBeInTheDocument()
    expect(screen.getByText('INACTIVO', { selector: 'span.status-pill' })).toBeInTheDocument()
    expect(screen.queryByText('Conectado')).not.toBeInTheDocument()
  })

  it('permite a OPERADOR cambiar modo y estado sin editar nombre', async () => {
    getCurrentUser.mockResolvedValue({ id_usuario: 3, login: 'operador.prueba', rol: 'OPERADOR' })
    getDevice.mockResolvedValue(device)
    changeDeviceMode.mockResolvedValue({ ...device, modo_operacion: 'SALIDA' })
    changeDeviceState.mockResolvedValue({ ...device, modo_operacion: 'SALIDA', estado: 'ACTIVO' })
    renderResources('/dispositivos-edge/8')
    await screen.findByRole('heading', { name: 'Nodo ficticio' })
    expect(screen.queryByRole('heading', { name: 'Editar nombre' })).not.toBeInTheDocument()
    const stateSection = screen.getByRole('heading', { name: 'Estado administrativo' }).closest('.form-panel')
    const modeSection = screen.getByRole('heading', { name: 'Modo de operación' }).closest('.form-panel')
    await userEvent.selectOptions(screen.getByLabelText('Modo'), 'SALIDA')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar modo' }))
    expect(within(modeSection).getByRole('group', { name: /Cambiar el modo del dispositivo D-PRUEBA a SALIDA/ })).toBeInTheDocument()
    expect(within(stateSection).queryByRole('group')).not.toBeInTheDocument()
    expect(within(stateSection).getByRole('button', { name: 'Activar dispositivo' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus()
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(changeDeviceMode).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Guardar modo' })).toHaveFocus())
    await userEvent.click(screen.getByRole('button', { name: 'Guardar modo' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar cambio de modo' }))
    await waitFor(() => expect(changeDeviceMode).toHaveBeenCalledWith('8', 'SALIDA'))
    await userEvent.click(screen.getByRole('button', { name: 'Activar dispositivo' }))
    expect(within(stateSection).getByRole('group', { name: /Cambiar el estado del dispositivo D-PRUEBA a ACTIVO/ })).toBeInTheDocument()
    expect(within(modeSection).queryByRole('group')).not.toBeInTheDocument()
    const saveMode = within(modeSection).getByRole('button', { name: 'Guardar modo' })
    expect(saveMode).toBeDisabled()
    expect(saveMode).toHaveClass('device-mode-save')
    expect(within(modeSection).getByText('Hay un cambio de estado pendiente de confirmación.')).toBeInTheDocument()
    await userEvent.click(saveMode)
    expect(changeDeviceMode).toHaveBeenCalledTimes(1)
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(changeDeviceState).not.toHaveBeenCalled()
    await waitFor(() => expect(within(stateSection).getByRole('button', { name: 'Activar dispositivo' })).toHaveFocus())
    await userEvent.click(screen.getByRole('button', { name: 'Activar dispositivo' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar cambio de estado' }))
    await waitFor(() => expect(changeDeviceState).toHaveBeenCalledWith('8', 'ACTIVO'))
    expect(editDevice).not.toHaveBeenCalled()
  })

  it('edita solo el nombre del dispositivo y comunica una denegación de modo', async () => {
    getDevice.mockResolvedValue(device)
    editDevice.mockResolvedValue({ ...device, nombre: 'Nodo actualizado' })
    changeDeviceMode.mockRejectedValue({ status: 403, message: 'Permiso denegado.' })
    renderResources('/dispositivos-edge/8')
    await screen.findByRole('heading', { name: 'Editar nombre' })
    const heading = screen.getByRole('heading', { name: 'Información administrativa' })
    expect(within(heading.parentElement).getByText('INACTIVO')).toHaveClass('status-pill')
    expect(document.querySelectorAll('.status-pill')).toHaveLength(1)
    await userEvent.click(screen.getByRole('button', { name: 'Guardar nombre' }))
    expect(editDevice).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Confirmar edición' })).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Nombre *'), { target: { value: '  Nodo ficticio  ' } })
    await userEvent.click(screen.getByRole('button', { name: 'Guardar nombre' }))
    expect(editDevice).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Confirmar edición' })).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Nombre *'), { target: { value: 'Nodo actualizado' } })
    await userEvent.click(screen.getByRole('button', { name: 'Guardar nombre' }))
    const editSection = screen.getByRole('heading', { name: 'Editar nombre' }).closest('.form-panel')
    expect(within(editSection).getByRole('group', { name: /Cambiar el nombre del dispositivo/ })).toHaveTextContent('Nombre actual: «Nodo ficticio». Nombre propuesto: «Nodo actualizado».')
    expect(screen.getByRole('button', { name: 'Activar dispositivo' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Guardar modo' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(editDevice).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Guardar nombre' })).toHaveFocus())
    await userEvent.click(screen.getByRole('button', { name: 'Guardar nombre' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar edición' }))
    await waitFor(() => expect(editDevice).toHaveBeenCalledWith('8', 'Nodo actualizado'))
    await userEvent.selectOptions(screen.getByLabelText('Modo'), 'SALIDA')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar modo' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar cambio de modo' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Permiso denegado.')
  })
})
