import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearCsrf, request } from '../api/http.js'
import { getAccessAlertCounts, getAccessIncident, listAccessHistory,
  registerManualAccess, searchEligiblePeople } from '../api/eventos.js'
import { adminFiltersToApi, bogotaDayStart, nextBogotaDayStart,
  validateAdminFilters } from '../access/format.js'

const KEY = '11111111-1111-4111-8111-111111111111'
const BODY = { id_persona: 3, id_punto_acceso: 7, tipo_movimiento: 'ENTRADA' }
const event = { id_evento_acceso: 9, ...BODY, resultado: 'AUTORIZADO',
  metodo_registro: 'MANUAL', id_usuario_registrador: 2,
  fecha_hora_ocurrencia: '2026-10-25T15:00:00+00:00',
  tipo_incidencia_secuencia: null, id_dispositivo: null }
const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), {
  status, headers: { 'Content-Type': 'application/json', ...headers },
})

describe('contratos de Eventos de Acceso y cliente compatible', () => {
  beforeEach(() => { clearCsrf(); vi.stubGlobal('fetch', vi.fn()) })
  afterEach(() => { vi.unstubAllGlobals() })

  it('codifica la búsqueda elegible sin copiar datos a la ruta React ni persistirlos', async () => {
    const storage = vi.spyOn(Storage.prototype, 'setItem')
    fetch.mockResolvedValue(json({ personas: [] }))
    await searchEligiblePeople('documento', '  FICTICIO-0001  ')
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/eventos-acceso/personas-elegibles?criterio=documento&valor=FICTICIO-0001')
    expect(storage).not.toHaveBeenCalled()
  })

  it('conserva el JSON de 0007 y solo expone metadatos en la operación manual', async () => {
    fetch.mockResolvedValueOnce(json({ csrf_token: 'csrf-ficticio' }))
      .mockResolvedValueOnce(json(event, 201, { 'Idempotent-Replay': 'false' }))
      .mockResolvedValueOnce(json(event, 200, { 'Idempotent-Replay': 'true' }))
      .mockResolvedValueOnce(json({ puntos: [] }))
    const fresh = await registerManualAccess(BODY, KEY)
    const replay = await registerManualAccess(BODY, KEY)
    const oldClient = await request('/puntos-acceso')
    expect(fresh).toEqual({ data: event, status: 201, idempotentReplay: false })
    expect(replay).toEqual({ data: event, status: 200, idempotentReplay: true })
    expect(oldClient).toEqual({ puntos: [] })
    for (const [, options] of fetch.mock.calls.slice(1, 3)) {
      expect(options.headers).toEqual({
        Accept: 'application/json', 'Content-Type': 'application/json',
        'X-CSRF-Token': 'csrf-ficticio', 'Idempotency-Key': KEY,
      })
      expect(JSON.parse(options.body)).toEqual(BODY)
      expect(options.credentials).toBe('same-origin')
      expect(options.cache).toBe('no-store')
    }
  })

  it('restringe la cabecera idempotente al POST manual y UUIDv4 canónico', async () => {
    await expect(request('/puntos-acceso', { idempotencyKey: KEY })).rejects.toThrow()
    await expect(registerManualAccess(BODY, 'NO-UUID')).rejects.toThrow()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('distingue fallo previo al POST de un resultado de escritura incierto', async () => {
    fetch.mockRejectedValueOnce(new TypeError('red en CSRF'))
    await expect(registerManualAccess(BODY, KEY)).rejects.toMatchObject({
      status: 0, writeAttempted: false,
    })
    expect(fetch).toHaveBeenCalledTimes(1)
    clearCsrf()
    fetch.mockResolvedValueOnce(json({ csrf_token: 'csrf-ficticio' }))
      .mockRejectedValueOnce(new TypeError('red tras POST'))
    await expect(registerManualAccess(BODY, KEY)).rejects.toMatchObject({
      status: 0, writeAttempted: true,
    })
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it.each([400, 401, 403, 404, 409, 503])('conserva el HTTP %s de la escritura', async (status) => {
    fetch.mockResolvedValueOnce(json({ csrf_token: 'csrf-ficticio' }))
      .mockResolvedValueOnce(json({ error: 'Error ficticio' }, status))
    await expect(registerManualAccess(BODY, KEY)).rejects.toMatchObject({
      status, message: 'Error ficticio', writeAttempted: true,
    })
  })

  it('usa fechas civiles de Bogotá y límite superior exclusivo, sin zona del navegador', () => {
    expect(bogotaDayStart('2026-10-25')).toBe('2026-10-25T05:00:00.000Z')
    expect(nextBogotaDayStart('2026-10-25')).toBe('2026-10-26T05:00:00.000Z')
    expect(adminFiltersToApi({ id_persona: '3', desde: '2026-10-25', hasta: '2026-10-25' }))
      .toMatchObject({ id_persona: '3', desde: '2026-10-25T05:00:00.000Z',
        hasta: '2026-10-26T05:00:00.000Z' })
    expect(validateAdminFilters({ desde: '2026-10-26', hasta: '2026-10-25' })).toMatch(/día final/)
    expect(validateAdminFilters({ id_persona: '0' })).toMatch(/identificadores/)
    expect(() => bogotaDayStart('2026-02-30')).toThrow()
  })

  it('envía solo filtros administrativos permitidos, consulta agregados y detalle existente', async () => {
    fetch.mockResolvedValueOnce(json({ eventos: [], limite: 20, desplazamiento: 0 }))
      .mockResolvedValueOnce(json({ conteos_por_incidencia: {}, zona_horaria: 'America/Bogota' }))
      .mockResolvedValueOnce(json({ id_evento_acceso: 9 }))
    await listAccessHistory({ id_persona: '3', desde: '2026-10-25', hasta: '2026-10-25' })
    await getAccessAlertCounts()
    await getAccessIncident('9')
    expect(fetch.mock.calls[0][0]).toContain('id_persona=3')
    expect(fetch.mock.calls[0][0]).toContain('desde=2026-10-25T05%3A00%3A00.000Z')
    expect(fetch.mock.calls[0][0]).toContain('hasta=2026-10-26T05%3A00%3A00.000Z')
    expect(fetch.mock.calls[1][0]).toBe('/api/v1/eventos-acceso/alertas')
    expect(fetch.mock.calls[2][0]).toBe('/api/v1/eventos-acceso/incidencias/9')
  })
})
