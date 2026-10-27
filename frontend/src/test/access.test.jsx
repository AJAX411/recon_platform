import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { App } from '../App.jsx'
import { PendingManualProvider } from '../access/PendingManualProvider.jsx'
import { usePendingManual } from '../access/usePendingManual.js'
import { AuthProvider } from '../auth/AuthContext.jsx'
import { AuthContext } from '../auth/context.js'
import { ApiError } from '../api/http.js'

vi.mock('../api/auth.js', () => ({ getCurrentUser: vi.fn(), login: vi.fn(), logout: vi.fn() }))
vi.mock('../api/eventos.js', () => ({
  searchEligiblePeople: vi.fn(), registerManualAccess: vi.fn(), listAccessHistory: vi.fn(),
  listAccessAlerts: vi.fn(), getAccessAlertCounts: vi.fn(), getAccessIncident: vi.fn(),
}))
vi.mock('../api/puntos.js', async (importOriginal) => ({
  ...await importOriginal(), listPoints: vi.fn(),
}))

import { getCurrentUser, logout } from '../api/auth.js'
import { listPoints } from '../api/puntos.js'
import { searchEligiblePeople, registerManualAccess, listAccessHistory,
  listAccessAlerts, getAccessAlertCounts, getAccessIncident } from '../api/eventos.js'

const ADMIN = { id_usuario: 2, login: 'admin.ficticio', rol: 'ADMINISTRADOR' }
const OPERATOR = { id_usuario: 3, login: 'operador.ficticio', rol: 'OPERADOR' }
const SUPER = { id_usuario: 1, login: 'super.ficticio', rol: 'SUPERADMIN' }
const KEY = '11111111-1111-4111-8111-111111111111'
const person = { id_persona: 4, nombre: 'Ana Ficticia', tipo_documento: 'CC', documento_final: '0001' }
const point = { id_punto_acceso: 7, codigo: 'P-PRUEBA', nombre: 'Punto ficticio', estado: 'ACTIVO' }
const event = { id_evento_acceso: 9, id_persona: 4, id_punto_acceso: 7,
  tipo_movimiento: 'ENTRADA', resultado: 'AUTORIZADO', metodo_registro: 'MANUAL',
  id_usuario_registrador: 2, fecha_hora_ocurrencia: '2026-10-25T15:00:00+00:00',
  tipo_incidencia_secuencia: 'ENTRADA_REPETIDA', id_dispositivo: null }
const adminRow = { ...event, nombre_persona: 'Ana Ficticia', tipo_documento: 'CC',
  numero_documento: 'FICTICIO-0001', punto: 'Punto ficticio', usuario_registrador: 'admin.ficticio' }
const history = (eventos) => ({ eventos, limite: 20, desplazamiento: 0, alcance: 'JORNADA_ACTUAL_REDUCIDA' })
const alerts = (rows) => ({ alertas: rows, limite: 20, desplazamiento: 0 })

function renderApp(path) {
  return render(<MemoryRouter initialEntries={[path]}><AuthProvider><App /></AuthProvider></MemoryRouter>)
}

async function chooseManual() {
  await screen.findByRole('heading', { name: 'Registrar entrada o salida' })
  fireEvent.change(screen.getByLabelText('Valor de búsqueda'), { target: { value: 'Ana' } })
  await userEvent.click(screen.getByRole('button', { name: 'Buscar Persona' }))
  await screen.findByRole('option', { name: /Ana Ficticia.*ID 4/ })
  await userEvent.selectOptions(screen.getByLabelText(/Seleccionar Persona/), '4')
  await userEvent.click(await screen.findByRole('button', { name: 'Seleccionar' }))
  await userEvent.selectOptions(screen.getByLabelText(/Tipo de movimiento/), 'ENTRADA')
}

async function confirmManual() {
  await userEvent.click(screen.getByRole('button', { name: 'Revisar declaración' }))
  await userEvent.click(screen.getByRole('button', { name: 'Confirmar registro' }))
}

describe('frontend 0008 con datos ficticios', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('crypto', { randomUUID: vi.fn().mockReturnValue(KEY) })
    getCurrentUser.mockResolvedValue(ADMIN)
    listPoints.mockResolvedValue({ puntos: [point], limite: 20, desplazamiento: 0 })
    searchEligiblePeople.mockResolvedValue({ personas: [person,
      { ...person, id_persona: 5, documento_final: '0002' }] })
    registerManualAccess.mockResolvedValue({ data: event, status: 201, idempotentReplay: false })
    listAccessHistory.mockResolvedValue(history([]))
    listAccessAlerts.mockResolvedValue(alerts([]))
    getAccessAlertCounts.mockResolvedValue({
      conteos_por_incidencia: {}, zona_horaria: 'America/Bogota',
    })
    getAccessIncident.mockResolvedValue(adminRow)
  })
  afterEach(() => { vi.unstubAllGlobals() })

  it('usa selector elegible, diferencia homónimos y exige selección explícita', async () => {
    getCurrentUser.mockResolvedValue(OPERATOR)
    renderApp('/eventos-acceso/manual')
    await screen.findByRole('heading', { name: 'Registrar entrada o salida' })
    await userEvent.click(screen.getByRole('button', { name: 'Revisar declaración' }))
    expect(screen.getByText('Selecciona una Persona elegible.')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Valor de búsqueda'), { target: { value: 'Ana' } })
    await userEvent.click(screen.getByRole('button', { name: 'Buscar Persona' }))
    expect(searchEligiblePeople).toHaveBeenCalledWith('nombre', 'Ana', expect.any(AbortSignal))
    expect(await screen.findByRole('option', { name: /ID 4/ })).toHaveTextContent('0001')
    expect(screen.getByRole('option', { name: /ID 5/ })).toHaveTextContent('0002')
    await userEvent.selectOptions(screen.getByLabelText(/Seleccionar Persona/), '4')
    fireEvent.change(screen.getByLabelText('Valor de búsqueda'), { target: { value: 'Analia' } })
    expect(screen.queryByRole('option', { name: /ID 4/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Personas' })).not.toBeInTheDocument()
    expect(registerManualAccess).not.toHaveBeenCalled()
  })

  it('selecciona solo Puntos activos, filtra por código y vuelve desde página vacía', async () => {
    const full = Array.from({ length: 20 }, (_, index) => ({ ...point,
      id_punto_acceso: index + 1, codigo: `P${index}` }))
    listPoints.mockResolvedValueOnce({ puntos: full, limite: 20, desplazamiento: 0 })
      .mockResolvedValueOnce({ puntos: [], limite: 20, desplazamiento: 20 })
      .mockResolvedValueOnce({ puntos: [point], limite: 20, desplazamiento: 0 })
    renderApp('/eventos-acceso/manual')
    await screen.findByRole('heading', { name: 'Registrar entrada o salida' })
    expect(await screen.findByRole('rowheader', { name: 'P0' })).toBeInTheDocument()
    expect(listPoints).toHaveBeenCalledWith({ estado: 'ACTIVO', codigo: '' }, 0, 20, expect.any(AbortSignal))
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByText('No hay Puntos activos en esta página.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Anterior' }))
    await screen.findByRole('rowheader', { name: 'P-PRUEBA' })
    fireEvent.change(screen.getByLabelText('Código exacto (opcional)'), { target: { value: 'P-PRUEBA' } })
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtro' }))
    await waitFor(() => expect(listPoints).toHaveBeenLastCalledWith(
      { estado: 'ACTIVO', codigo: 'P-PRUEBA' }, 0, 20, expect.any(AbortSignal)))
  })

  it('cancela sin POST, devuelve foco y confirma una sola vez aun con clics rápidos', async () => {
    let resolveWrite
    registerManualAccess.mockImplementation(() => new Promise((resolve) => { resolveWrite = resolve }))
    const storage = vi.spyOn(Storage.prototype, 'setItem')
    renderApp('/eventos-acceso/manual')
    await chooseManual()
    await userEvent.click(screen.getByRole('button', { name: 'Revisar declaración' }))
    const panel = screen.getByRole('group', { name: 'Confirmar movimiento manual' })
    expect(within(panel).getByText(/Ana Ficticia/)).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Cancelar' })).toHaveFocus()
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(registerManualAccess).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Revisar declaración' })).toHaveFocus())
    await userEvent.click(screen.getByRole('button', { name: 'Revisar declaración' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar registro' }))
    await waitFor(() => expect(registerManualAccess).toHaveBeenCalledTimes(1))
    const progressPanel = screen.getByRole('heading', { name: 'Enviando declaración' }).closest('section')
    await waitFor(() => expect(progressPanel).toHaveFocus())
    expect(registerManualAccess).toHaveBeenCalledWith({
      id_persona: 4, id_punto_acceso: 7, tipo_movimiento: 'ENTRADA',
    }, KEY)
    expect(crypto.randomUUID).toHaveBeenCalledTimes(1)
    expect(storage).not.toHaveBeenCalled()
    await act(async () => resolveWrite({ data: event, status: 201, idempotentReplay: false }))
    const resultPanel = (await screen.findByRole('heading', { name: 'Declaración registrada' })).closest('section')
    expect(resultPanel).toBe(progressPanel)
    await waitFor(() => expect(resultPanel).toHaveFocus())
    expect(screen.getByText('AUTORIZADO')).toBeInTheDocument()
    expect(screen.getByText('MANUAL')).toBeInTheDocument()
    expect(screen.getByText(/Entrada repetida/)).toBeInTheDocument()
  })

  it('reconoce replay 200 y restringe el detalle en el resultado de OPERADOR', async () => {
    getCurrentUser.mockResolvedValue(OPERATOR)
    registerManualAccess.mockResolvedValue({ data: event, status: 200, idempotentReplay: true })
    renderApp('/eventos-acceso/manual')
    await chooseManual()
    await confirmManual()
    expect(await screen.findByRole('heading', { name: 'Declaración ya registrada' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Consultar incidencia' })).not.toBeInTheDocument()
    expect(screen.queryByText('ID del evento')).not.toBeInTheDocument()
  })

  it.each([0, 503])('conserva clave, cuerpo y actor tras resultado incierto %s', async (status) => {
    registerManualAccess.mockRejectedValueOnce({ status, writeAttempted: true })
      .mockResolvedValueOnce({ data: event, status: 200, idempotentReplay: true })
    const view = renderApp('/eventos-acceso/manual')
    await chooseManual()
    await confirmManual()
    expect(await screen.findByText(/No se pudo confirmar si la declaración quedó registrada/)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'No se confirmó el registro' }).closest('section')).toHaveFocus())
    expect(registerManualAccess).toHaveBeenCalledTimes(1)
    expect(screen.getByLabelText(/Tipo de movimiento/)).toBeDisabled()
    const beforeUnload = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(beforeUnload)
    expect(beforeUnload.defaultPrevented).toBe(true)
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar la misma declaración' }))
    await waitFor(() => expect(registerManualAccess).toHaveBeenCalledTimes(2))
    expect(registerManualAccess.mock.calls[1][0]).toBe(registerManualAccess.mock.calls[0][0])
    expect(registerManualAccess.mock.calls[1][1]).toBe(KEY)
    expect(crypto.randomUUID).toHaveBeenCalledTimes(1)
    expect(await screen.findByRole('heading', { name: 'Declaración ya registrada' })).toBeInTheDocument()
    view.unmount()
  })

  it('advierte antes de cerrar sesión con una declaración incierta', async () => {
    registerManualAccess.mockRejectedValue({ status: 503, writeAttempted: true })
    const confirmExit = vi.fn().mockReturnValue(false)
    vi.stubGlobal('confirm', confirmExit)
    renderApp('/eventos-acceso/manual')
    await chooseManual()
    await confirmManual()
    await screen.findByText(/No se pudo confirmar si la declaración quedó registrada/)
    await userEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    expect(confirmExit).toHaveBeenCalledTimes(1)
    expect(logout).not.toHaveBeenCalled()
    confirmExit.mockReturnValue(true)
    await userEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(logout).toHaveBeenCalledTimes(1)
  })

  it('distingue fallo de preparación y no promete recuperar la clave tras recarga', async () => {
    registerManualAccess.mockRejectedValueOnce({ status: 0, writeAttempted: false })
    const first = renderApp('/eventos-acceso/manual')
    await chooseManual()
    await confirmManual()
    expect(await screen.findByText(/No se envió la declaración/)).toBeInTheDocument()
    first.unmount()
    renderApp('/eventos-acceso/manual')
    await screen.findByRole('heading', { name: 'Registrar entrada o salida' })
    expect(screen.queryByRole('button', { name: 'Reintentar la misma declaración' })).not.toBeInTheDocument()
    expect(screen.getByText(/la clave en memoria no puede recuperarse/)).toBeInTheDocument()
  })

  it.each([400, 403, 404, 409])('comunica rechazo HTTP %s sin rotar clave', async (status) => {
    registerManualAccess.mockRejectedValueOnce({ status, writeAttempted: true,
      message: `Error ficticio ${status}` })
    renderApp('/eventos-acceso/manual')
    await chooseManual()
    await confirmManual()
    expect(await screen.findByText(`Error ficticio ${status}`)).toBeInTheDocument()
    expect(registerManualAccess).toHaveBeenCalledTimes(1)
    expect(crypto.randomUUID).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('button', { name: 'Reintentar la misma declaración' })).not.toBeInTheDocument()
  })

  it('reserva el detalle para administración aun en URL directa', async () => {
    getCurrentUser.mockResolvedValue(OPERATOR)
    renderApp('/eventos-acceso/incidencias/9')
    expect(await screen.findByRole('heading', { name: 'Bienvenido a Recon Facial' })).toBeInTheDocument()
    expect(getAccessIncident).not.toHaveBeenCalled()
    expect(screen.getByRole('link', { name: 'Registro manual' })).toBeInTheDocument()
  })

  it('muestra a OPERADOR solo historial reducido y permite volver de página vacía', async () => {
    getCurrentUser.mockResolvedValue(OPERATOR)
    const reduced = { tipo_movimiento: 'SALIDA', resultado: 'AUTORIZADO',
      hora_local_aproximada: '2026-10-25T09:00:00-05:00',
      nombre_persona: 'Dato que no debe renderizarse', id_persona: 99 }
    const full = Array.from({ length: 20 }, () => reduced)
    listAccessHistory.mockResolvedValueOnce(history(full))
      .mockResolvedValueOnce(history([])).mockResolvedValueOnce(history(full))
    renderApp('/eventos-acceso/historial')
    expect(await screen.findAllByRole('rowheader', { name: 'SALIDA' })).toHaveLength(20)
    expect(screen.queryByText('Dato que no debe renderizarse')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('ID de Persona')).not.toBeInTheDocument()
    expect(listAccessHistory).toHaveBeenCalledWith({}, 0, 20, expect.any(AbortSignal))
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByText('No hay movimientos en esta página.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Anterior' }))
    expect(await screen.findAllByRole('rowheader', { name: 'SALIDA' })).toHaveLength(20)
  })

  it('aplica filtros de administración y recupera un error de lectura', async () => {
    listAccessHistory.mockRejectedValueOnce({ status: 503, message: 'Consulta ficticia no disponible.' })
      .mockResolvedValue({ eventos: [adminRow], limite: 20, desplazamiento: 0, alcance: 'HISTORICO_AMPLIADO' })
    renderApp('/eventos-acceso/historial')
    expect(await screen.findByRole('alert')).toHaveTextContent('Consulta ficticia no disponible.')
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('rowheader', { name: 'ID 9' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('ID de Persona'), { target: { value: '4' } })
    fireEvent.change(screen.getByLabelText('Desde (día Bogotá)'), { target: { value: '2026-10-25' } })
    fireEvent.change(screen.getByLabelText('Hasta (día incluido, Bogotá)'), { target: { value: '2026-10-25' } })
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' }))
    await waitFor(() => expect(listAccessHistory).toHaveBeenLastCalledWith(
      expect.objectContaining({ id_persona: '4', desde: '2026-10-25', hasta: '2026-10-25' }),
      0, 20, expect.any(AbortSignal)))
  })

  it('presenta solo conteos de alertas a OPERADOR y actualiza a demanda', async () => {
    getCurrentUser.mockResolvedValue(OPERATOR)
    getAccessAlertCounts.mockResolvedValue({
      conteos_por_incidencia: { SALIDA_REPETIDA: 2 }, zona_horaria: 'America/Bogota',
    })
    renderApp('/eventos-acceso/alertas')
    expect(await screen.findByText('Salida repetida')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Siguiente' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar alertas' }))
    await waitFor(() => expect(getAccessAlertCounts).toHaveBeenCalledTimes(2))
  })

  it('lista incidencias administrativas y consulta el detalle autorizado', async () => {
    getCurrentUser.mockResolvedValue(SUPER)
    listAccessAlerts.mockResolvedValue(alerts([adminRow]))
    renderApp('/eventos-acceso/alertas')
    const detail = await screen.findByRole('link', { name: 'Consultar incidencia' })
    await userEvent.click(detail)
    expect(await screen.findByRole('heading', { name: 'Detalle de incidencia' })).toBeInTheDocument()
    expect(getAccessIncident).toHaveBeenCalledWith('9', expect.any(AbortSignal))
    expect(screen.getByText(/FICTICIO-0001/)).toBeInTheDocument()
  })

  it.each([403, 404])('informa %s al consultar un detalle administrativo', async (status) => {
    getAccessIncident.mockRejectedValue({ status, message: `Error ficticio ${status}` })
    renderApp('/eventos-acceso/incidencias/9')
    expect(await screen.findByRole('alert')).toHaveTextContent(`Error ficticio ${status}`)
  })

  it('rechaza un identificador de incidencia inválido sin llamar a la API', async () => {
    renderApp('/eventos-acceso/incidencias/invalido')
    expect(await screen.findByRole('alert')).toHaveTextContent('El identificador no es válido.')
    expect(getAccessIncident).not.toHaveBeenCalled()
  })

  it('impide acceso anónimo y descarta filas ampliadas al cambiar de rol', async () => {
    getCurrentUser.mockRejectedValueOnce(new ApiError('Sin sesión.', 401))
    const initial = renderApp('/eventos-acceso/manual')
    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    initial.unmount()

    const authAdmin = { user: ADMIN, status: 'authenticated', expire: vi.fn(), refresh: vi.fn(), signOut: vi.fn() }
    const authOperator = { ...authAdmin, user: OPERATOR }
    listAccessHistory.mockResolvedValueOnce({ eventos: [adminRow], limite: 20, desplazamiento: 0 })
      .mockResolvedValueOnce(history([{ tipo_movimiento: 'ENTRADA', resultado: 'AUTORIZADO',
        hora_local_aproximada: '2026-10-25T09:00:00-05:00' }]))
    const view = render(<MemoryRouter initialEntries={['/eventos-acceso/historial']}>
      <AuthContext.Provider value={authAdmin}><App /></AuthContext.Provider>
    </MemoryRouter>)
    expect(await screen.findByText('Ana Ficticia')).toBeInTheDocument()
    view.rerender(<MemoryRouter initialEntries={['/eventos-acceso/historial']}>
      <AuthContext.Provider value={authOperator}><App /></AuthContext.Provider>
    </MemoryRouter>)
    expect(await screen.findByRole('rowheader', { name: 'ENTRADA' })).toBeInTheDocument()
    expect(screen.queryByText('Ana Ficticia')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('ID de Persona')).not.toBeInTheDocument()
  })

  it('no transfiere una declaración incierta a otro actor', async () => {
    registerManualAccess.mockRejectedValue({ status: 503, writeAttempted: true })
    function Probe() {
      const { submission, start, retry } = usePendingManual()
      return <>
        <span>Estado {submission?.phase || 'vacío'}</span>
        <button onClick={() => {
          const body = { id_persona: 4, id_punto_acceso: 7, tipo_movimiento: 'ENTRADA' }
          start(body)
          start(body)
        }}>Declarar dos veces</button>
        <button onClick={retry}>Reintentar</button>
      </>
    }
    const authA = { user: ADMIN, expire: vi.fn() }
    const authB = { user: OPERATOR, expire: vi.fn() }
    const view = render(<AuthContext.Provider value={authA}><PendingManualProvider><Probe /></PendingManualProvider></AuthContext.Provider>)
    await userEvent.click(screen.getByRole('button', { name: 'Declarar dos veces' }))
    expect(await screen.findByText('Estado uncertain')).toBeInTheDocument()
    expect(registerManualAccess).toHaveBeenCalledTimes(1)
    expect(crypto.randomUUID).toHaveBeenCalledTimes(1)
    view.rerender(<AuthContext.Provider value={authB}><PendingManualProvider><Probe /></PendingManualProvider></AuthContext.Provider>)
    expect(await screen.findByText('Estado vacío')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(registerManualAccess).toHaveBeenCalledTimes(1)
  })
})
