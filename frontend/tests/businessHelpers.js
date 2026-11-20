import { appAt, identity, response } from './helpers.js'
import { pages } from '../src/pages/index.js'
import { vi } from 'vitest'

export const personData = { id_persona: 7, primer_nombre: 'Persona', segundo_nombre: null, primer_apellido: 'Ficticia', segundo_apellido: null,
  tipo_persona: 'VISITANTE', tipo_documento: 'CC', numero_documento: 'DOC-FICTICIO', identificador_institucional: null, estado: 'ACTIVO' }
export const pointData = { id_punto_acceso: 7, codigo: 'P7', nombre: 'Punto inactivo', descripcion: null, estado: 'INACTIVO' }
export const activePoint = { ...pointData, id_punto_acceso: 8, codigo: 'P8', nombre: 'Punto activo', estado: 'ACTIVO' }
export const deviceData = { id_dispositivo: 7, codigo: 'D7', nombre: 'Dispositivo ficticio', id_punto_acceso: 7,
  modo_operacion: 'AUTOMATICO', estado: 'INACTIVO', ultima_comunicacion: null }
export const documentTypes = ['CC', 'TI', 'CE', 'PA', 'PPT', 'RC'].map((codigo) => ({
  codigo, nombre: codigo === 'RC' ? 'Registro civil de nacimiento' : 'Documento ' + codigo, habilitado_para_altas: true,
}))
export const roles = ['SUPERADMIN', 'ADMINISTRADOR', 'OPERADOR'].map((nombre) => ({ nombre, asignable: nombre !== 'SUPERADMIN' }))
export function fixtureServer(overrides = {}, role = 'SUPERADMIN') {
  const state = {
    people: { 7: { ...personData } },
    users: { 1: { id_usuario: 1, login: 'super-ficticio', rol: 'SUPERADMIN', estado: 'ACTIVO' },
      7: { id_usuario: 7, login: 'operador-ficticio', rol: 'OPERADOR', estado: 'ACTIVO' } },
    points: { 7: { ...pointData }, 8: { ...activePoint } }, devices: { 7: { ...deviceData } }, next: 100,
    declarations: new Map(),
    role,
  }
  const collections = { '/personas': ['people', 'personas', 'id_persona'],
    '/iam/usuarios': ['users', 'usuarios', 'id_usuario'],
    '/puntos-acceso': ['points', 'puntos', 'id_punto_acceso'],
    '/dispositivos-edge': ['devices', 'dispositivos', 'id_dispositivo'] }
  function handler(path, options) {
    const url = new URL(path, 'http://fixture.local')
    if (overrides[url.pathname]) {
      const result = overrides[url.pathname](url, options, state)
      if (result !== undefined) return result
    }
    if (url.pathname === '/personas/tipos') return response({ tipos: [
      { id_tipo_persona: 1, nombre: 'VISITANTE', estado: 'ACTIVO' }, { id_tipo_persona: 2, nombre: 'ESTUDIANTE', estado: 'ACTIVO' },
    ] })
    if (url.pathname === '/personas/tipos-documento') return response({ tipos_documento: documentTypes })
    if (url.pathname === '/iam/roles') return response({ roles })
    for (const [base, [name, collection, idKey]] of Object.entries(collections)) {
      if (url.pathname !== base && !url.pathname.startsWith(base + '/')) continue
      if (url.pathname === base) {
        if (options.method === 'GET') {
          let rows = Object.values(state[name])
          for (const key of ['estado', 'codigo', 'tipo_persona', 'tipo_documento']) {
            if (url.searchParams.get(key)) rows = rows.filter((r) => r[key] === url.searchParams.get(key))
          }
          const offset = Number(url.searchParams.get('desplazamiento') || 0)
          return response({ [collection]: rows.slice(offset, offset + 20) })
        }
        const body = JSON.parse(options.body)
        const id = state.next++
        const saved = { ...body, [idKey]: id, estado: name === 'devices' ? 'INACTIVO' : 'ACTIVO' }
        delete saved.contrasena
        if (name === 'users') saved.login = saved.login.toLowerCase()
        if (name === 'devices') saved.ultima_comunicacion = null
        state[name][id] = saved
        return response(saved, 201)
      }
      const [idText, action] = url.pathname.slice(base.length + 1).split('/')
      const data = state[name][idText]
      if (!data) return response({ error: 'No existe' }, 404)
      if (options.method === 'GET') return response({ ...data })
      const body = JSON.parse(options.body)
      Object.assign(data, body)
      if (action === 'modo') data.modo_operacion = body.modo_operacion
      return response({ ...data })
    }
    if (url.pathname === '/eventos-acceso/personas-elegibles') return response({ personas: Object.values(state.people)
      .filter((p) => p.estado === 'ACTIVO').map((p) => ({ id_persona: p.id_persona, nombre: p.primer_nombre + ' ' + p.primer_apellido,
        tipo_documento: p.tipo_documento, documento_final: '1234' })) })
    if (url.pathname === '/eventos-acceso/manual') {
      const body = JSON.parse(options.body), key = options.headers['Idempotency-Key']
      if (state.declarations.has(key)) {
        const data = state.declarations.get(key)
        if (data.id_persona !== body.id_persona || data.id_punto_acceso !== body.id_punto_acceso || data.tipo_movimiento !== body.tipo_movimiento) return response({ error: 'Clave incompatible' }, 409)
        return response(data, 200, { 'Idempotent-Replay': 'true' })
      }
      if (state.people[body.id_persona]?.estado !== 'ACTIVO' || state.points[body.id_punto_acceso]?.estado !== 'ACTIVO') return response({ error: 'Referencia no disponible' }, 404)
      const data = { ...manualResponse(body), id_evento_acceso: 1000 + state.declarations.size }
      state.declarations.set(key, data)
      return response(data, 201)
    }
    if (url.pathname === '/eventos-acceso/historial' || url.pathname === '/eventos-acceso/alertas') {
      const records = [...state.declarations.values()]
      if (url.pathname.endsWith('/alertas') && state.role === 'OPERADOR') return response({
        conteos_por_incidencia: Object.fromEntries(records.filter((d) => d.tipo_incidencia_secuencia).map((d) => [d.tipo_incidencia_secuencia, 1])),
      })
      const rows = state.role === 'OPERADOR' ? records.map((d) => ({ tipo_movimiento: d.tipo_movimiento, resultado: d.resultado,
        hora_local_aproximada: '2026-11-17T14:00:00Z' })) : records.map((d) => ({
        ...d, nombre_persona: state.people[d.id_persona].primer_nombre, punto: state.points[d.id_punto_acceso].nombre, usuario_registrador: 'cuenta-ficticia',
      }))
      return response({ [url.pathname.endsWith('/alertas') ? 'alertas' : 'eventos']: rows })
    }
    return undefined
  }
  return { state, handler }
}
export async function businessApp(path, role = 'SUPERADMIN', overrides = {}) {
  const server = fixtureServer(overrides, role)
  const mounted = await appAt(path, identity(role), { '*': server.handler }, pages)
  return { ...mounted, state: server.state }
}
export function input(id, value) {
  const target = document.getElementById(id)
  if (!target) throw new Error('No existe el control ' + id)
  target.value = value
  target.dispatchEvent(new Event(target.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }))
  return target
}
export const submit = () => document.querySelector('main form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
export const writes = (fetcher) => fetcher.mock.calls.filter(([url, options]) => options.method !== 'GET' && !url.includes('/auth/'))
export async function waitText(text) {
  await vi.waitFor(() => { if (!document.querySelector('main')?.textContent.includes(text)) throw new Error('Esperando ' + text) })
}
export async function readyPerson() {
  await vi.waitFor(() => { if (document.querySelector('#tipo_documento')?.options.length < 7) throw new Error('Esperando catálogos') })
}
export function fillPerson(extra = {}) {
  for (const [key, value] of Object.entries({ primer_nombre: 'Nueva', primer_apellido: 'Ficticia', tipo_persona: 'VISITANTE',
    tipo_documento: 'CC', numero_documento: 'DOC-NUEVO', ...extra })) input(key, value)
}
export function dialogButton(text) {
  const controls = [...document.querySelectorAll('dialog button')]
  return text ? controls.find((node) => node.textContent === text)
    : controls.find((node) => node.classList.contains('btn-primary'))
}
export function manualResponse(body = { id_persona: 7, id_punto_acceso: 8, tipo_movimiento: 'ENTRADA' }) {
  return { ...body, id_evento_acceso: 99, resultado: 'AUTORIZADO', metodo_registro: 'MANUAL',
    id_usuario_registrador: 1, id_dispositivo: null, fecha_hora_ocurrencia: '2026-11-17T14:42:11Z',
    tipo_incidencia_secuencia: body.tipo_movimiento === 'SALIDA' ? 'SALIDA_SIN_ENTRADA_DEL_DIA' : null }
}
