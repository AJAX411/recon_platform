import { afterEach, describe, expect, it, vi } from 'vitest'
import { pages } from '../src/pages/index.js'
import { routes } from '../src/routes.js'
import { appAt, click, dashboardData, deferred, findButton, identity, response } from './helpers.js'

const person = { id_persona: 7, primer_nombre: '<img src=x onerror=alert(1)>', segundo_nombre: null,
  primer_apellido: 'Ejemplo', segundo_apellido: null, tipo_documento: 'PRUEBA', numero_documento: 'DOC-FICTICIO',
  identificador_institucional: null, tipo_persona: 'VISITANTE', estado: 'ACTIVO' }
const account = { id_usuario: 7, login: 'usuario-ejemplo', rol: 'OPERADOR', estado: 'ACTIVO' }
const point = { id_punto_acceso: 7, codigo: 'P-FICTICIO', nombre: 'Punto de prueba', descripcion: null, estado: 'ACTIVO' }
const device = { id_dispositivo: 7, codigo: 'D-FICTICIO', nombre: 'Nodo de prueba', id_punto_acceso: 7,
  modo_operacion: 'AUTOMATICO', estado: 'INACTIVO', ultima_comunicacion: null }
const movement = { id_evento_acceso: 9, nombre_persona: 'Persona del movimiento', punto: 'Punto de prueba',
  tipo_movimiento: 'ENTRADA', resultado: 'AUTORIZADO', fecha_hora_ocurrencia: '2026-11-17T14:42:11Z',
  tipo_incidencia_secuencia: 'ENTRADA_REPETIDA', usuario_registrador: 'actor-ficticio',
  tipo_documento: 'CC', numero_documento: 'DOCUMENTO-SOLO-INCIDENCIA', id_persona: 7, id_punto_acceso: 7,
  id_usuario_registrador: 7, metodo_registro: 'MANUAL', id_dispositivo: null }
const reduced = { tipo_movimiento: 'SALIDA', resultado: 'AUTORIZADO', hora_local_aproximada: '2026-11-17T09:00:00-05:00' }
const cleanups = []
afterEach(() => { while (cleanups.length) cleanups.pop()() })
function handler(role, extra = {}) {
  return (path, options) => {
    const url = new URL(path, 'http://fixture.local')
    if (extra[url.pathname]) return extra[url.pathname](url, options)
    if (url.pathname === '/personas/tipos') return response({ tipos: [{ nombre: 'VISITANTE', estado: 'ACTIVO' }] })
    if (url.pathname === '/personas/tipos-documento') return response({ tipos_documento: [
      { codigo: 'CC', nombre: 'Cédula de ciudadanía', habilitado_para_altas: true },
    ] })
    if (url.pathname === '/personas') return response({ personas: [person] })
    if (url.pathname === '/personas/7') return response(person)
    if (url.pathname === '/iam/usuarios') return response({ usuarios: [account] })
    if (url.pathname === '/iam/usuarios/7') return response(account)
    if (url.pathname === '/puntos-acceso') return response({ puntos: [point] })
    if (url.pathname === '/puntos-acceso/7') return response(point)
    if (url.pathname === '/dispositivos-edge') return response({ dispositivos: [device] })
    if (url.pathname === '/dispositivos-edge/7') return response(device)
    if (url.pathname === '/eventos-acceso/historial') return response({ eventos: role === 'OPERADOR' ? [reduced] : [movement] })
    if (url.pathname === '/eventos-acceso/alertas') return response(role === 'OPERADOR'
      ? { conteos_por_incidencia: { ENTRADA_REPETIDA: 4 }, zona_horaria: 'America/Bogota' } : { alertas: [movement] })
    if (url.pathname === '/eventos-acceso/incidencias/9') return response(movement)
    return undefined
  }
}
async function mount(path, role = 'SUPERADMIN', extra = {}, specials = {}) {
  const result = await appAt(path, identity(role), { '*': handler(role, extra), ...specials }, pages)
  cleanups.push(result.stop)
  return result
}
async function settled(text) {
  await vi.waitFor(() => expect(document.querySelector('main').textContent).toContain(text))
}
function submit(form) { form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })) }

describe('A2 · lectura y UX docente', () => {
  it.each([
    ['/personas', '<img'], ['/usuarios', 'usuario-ejemplo'],
    ['/puntos-acceso', 'P-FICTICIO'], ['/dispositivos-edge', 'D-FICTICIO'],
  ])('lista poblada %s, dato por columna, ojo, caption y cero escrituras', async (path, value) => {
    const { fetcher } = await mount(path)
    await settled(value)
    const table = document.querySelector('main table')
    expect(table.querySelector('caption').textContent).not.toBe('')
    expect(table.querySelectorAll('tbody tr')).toHaveLength(1)
    expect(table.querySelectorAll('tbody tr td,tbody tr th').length).toBe(table.querySelectorAll('thead th').length)
    expect(table.querySelectorAll('tbody small,tbody br,tbody dl')).toHaveLength(0)
    expect(table.querySelector('[aria-label^="Ver detalles"] svg')).not.toBeNull()
    expect(document.querySelector('img')).toBeNull()
    expect(fetcher.mock.calls.every(([, o]) => o.method === 'GET')).toBe(true)
  })
  it.each([
    ['/personas/7', 'DOC-FICTICIO'], ['/usuarios/7', 'usuario-ejemplo'],
    ['/puntos-acceso/7', 'P-FICTICIO'], ['/dispositivos-edge/7', 'D-FICTICIO'],
  ])('detalle %s con allowlist, sin foto ni formulario de escritura', async (path, value) => {
    await mount(path)
    await settled(value)
    expect(document.querySelector('main form,main input[type=file],main img')).toBeNull()
    expect(document.querySelector('main').textContent).not.toContain('Fotografía')
    expect(document.querySelector('main').textContent).toContain('La baja lógica conserva')
  })
  it('catálogos consultados, histórico literal y filtro exacto sin convertirlo en alta', async () => {
    const { fetcher } = await mount('/personas')
    await settled('PRUEBA')
    await vi.waitFor(() => expect(document.querySelector('#filtro-tipo_persona').options.length).toBe(2))
    document.querySelector('#filtro-tipo_documento').value = 'PRUEBA'
    submit(document.querySelector('main form'))
    await vi.waitFor(() => expect(fetcher.mock.calls.some(([u]) => u.includes('tipo_documento=PRUEBA'))).toBe(true))
    await settled('PRUEBA')
    expect(document.querySelector('main').textContent).toContain('PRUEBA')
    expect(document.querySelector('main').textContent).not.toContain('Valor convertido')
  })
  it('catálogo caído conserva listado/código y no presenta éxito del catálogo', async () => {
    await mount('/personas', 'ADMINISTRADOR', {
      '/personas/tipos-documento': () => response({ error: 'Temporal' }, 503),
    })
    await settled('PRUEBA')
    await settled('Catálogo no disponible')
  })
  it('paginación acotada: página de 20 y siguiente vacía permite volver, sin total ficticio', async () => {
    const { fetcher } = await mount('/puntos-acceso', 'OPERADOR', {
      '/puntos-acceso': (url) => response({ puntos: Number(url.searchParams.get('desplazamiento')) === 0
        ? Array.from({ length: 20 }, (_, i) => ({ ...point, id_punto_acceso: i + 1 })) : [] }),
    })
    await settled('P-FICTICIO')
    click(findButton('Siguiente'))
    await settled('No hay registros')
    expect(findButton('Anterior').disabled).toBe(false)
    expect(findButton('Siguiente').disabled).toBe(true)
    click(findButton('Anterior')); await settled('P-FICTICIO')
    expect(fetcher.mock.calls.filter(([u]) => u.startsWith('/api/v1/puntos-acceso?')).every(([u]) => u.includes('limite=20'))).toBe(true)
  })
  it('filtros de Dispositivo usan ID real, validan antes del GET y conservan estados administrativos', async () => {
    const { fetcher } = await mount('/dispositivos-edge')
    await settled('D-FICTICIO')
    const before = fetcher.mock.calls.length
    document.querySelector('#filtro-id_punto_acceso').value = 'CODIGO-NO-ID'
    submit(document.querySelector('main form'))
    expect(fetcher.mock.calls.length).toBe(before)
    document.querySelector('#filtro-id_punto_acceso').value = '7'
    document.querySelector('#filtro-modo_operacion').value = 'SALIDA'
    submit(document.querySelector('main form'))
    await vi.waitFor(() => expect(fetcher.mock.calls.some(([u]) => u.includes('id_punto_acceso=7') && u.includes('modo_operacion=SALIDA'))).toBe(true))
  })
  it('error de listado no equivale a vacío; reintento solo GET', async () => {
    let attempt = 0
    const { fetcher } = await mount('/puntos-acceso', 'SUPERADMIN', {
      '/puntos-acceso': () => ++attempt === 1 ? response({ error: 'Consulta temporalmente caída' }, 503) : response({ puntos: [point] }),
    })
    await settled('Consulta temporalmente caída')
    expect(document.querySelector('main').textContent).not.toContain('No hay registros')
    click(findButton('Reintentar consulta'))
    await settled('P-FICTICIO')
    expect(fetcher.mock.calls.every(([, o]) => o.method === 'GET')).toBe(true)
  })
  it.each(['SUPERADMIN', 'ADMINISTRADOR'])('Inicio %s conserva métricas/null/estimación sin refresh permanente', async (role) => {
    await mount('/', role)
    await settled('Personas dentro (estimación)')
    expect(document.querySelector('main').textContent).toContain('No disponible')
    expect(document.querySelector('main').textContent).toContain('presencia desconocida')
    expect(findButton('Actualizar')).toBeUndefined()
    expect([...document.querySelectorAll('main a')].some((a) => a.textContent === 'Ver historial')).toBe(false)
  })
  it('OPERADOR muestra cantidades parciales de filas y hora aproximada, nunca agregados administrativos', async () => {
    const data = dashboardData('OPERADOR')
    data.ultimos_movimientos = [reduced]
    await mount('/', 'OPERADOR', {}, { '/consultas/dashboard': () => response(data) })
    await settled('Salidas mostradas')
    expect(document.querySelector('main').textContent).toContain('No es el total del día')
    expect(document.querySelector('main').textContent).not.toContain('Personas dentro')
    expect(document.querySelector('main table').querySelectorAll('thead th')).toHaveLength(3)
    expect(document.querySelector('main [aria-haspopup=dialog]')).toBeNull()
  })
  it('O rechaza snapshot administrativo o fila enriquecida en lugar de reutilizarla', async () => {
    const data = dashboardData('OPERADOR')
    data.ultimos_movimientos = [{ ...reduced, nombre_persona: 'PROHIBIDO-ROL-ANTERIOR' }]
    await mount('/', 'OPERADOR', {}, { '/consultas/dashboard': () => response(data) })
    await settled('proyección reducida')
    expect(document.body.textContent).not.toContain('PROHIBIDO-ROL-ANTERIOR')
    expect(document.querySelector('main .metric-grid')).toBeNull()
  })
  it('error inicial no fabrica ceros; error posterior conserva stale, y reentrar revalida', async () => {
    let attempt = 0
    const { app, fetcher } = await mount('/', 'SUPERADMIN', {}, {
      '/consultas/dashboard': () => ++attempt === 1 ? response({ error: 'Inicial caída' }, 503)
        : attempt === 3 ? response({ error: 'Lectura caída' }, 503) : response(dashboardData()),
    })
    await settled('Inicial caída')
    expect(document.querySelector('.metric-grid')).toBeNull()
    expect(document.querySelector('.alert-badge').hidden).toBe(true)
    click(findButton('Reintentar consulta')); await settled('Entradas de hoy')
    app.router.navigate('/puntos-acceso'); await settled('P-FICTICIO')
    app.router.navigate('/'); await settled('Datos desactualizados')
    expect(document.querySelector('main').textContent).toContain('Entradas de hoy')
    expect(fetcher.mock.calls.filter(([u]) => u.endsWith('/consultas/dashboard'))).toHaveLength(3)
  })
  it.each(['SUPERADMIN', 'ADMINISTRADOR'])('Historial %s usa modal local con X/Escape/foco/scroll y sin documento extra ni GET', async (role) => {
    const { fetcher, app } = await mount('/eventos-acceso/historial', role)
    await settled('Persona del movimiento')
    const action = document.querySelector('main button[aria-haspopup=dialog]')
    const calls = fetcher.mock.calls.length
    action.focus(); document.body.style.overflow = 'auto'
    click(action)
    const dialog = document.querySelector('dialog')
    expect(dialog.parentElement).toBe(document.body)
    expect(dialog.textContent).toContain('actor-ficticio')
    expect(dialog.textContent).not.toContain('DOCUMENTO-SOLO-INCIDENCIA')
    expect(fetcher.mock.calls).toHaveLength(calls)
    const target = dialog.querySelector('a')
    target.focus()
    dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true }))
    expect(document.activeElement).toBe(dialog.querySelector('button'))
    dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }))
    expect(document.querySelector('dialog')).toBeNull()
    expect(document.body.style.overflow).toBe('auto')
    expect(document.activeElement).toBe(action)
    click(action)
    app.router.navigate('/puntos-acceso')
    expect(document.querySelector('dialog')).toBeNull()
    expect(document.body.style.overflow).toBe('auto')
  })
  it('Inicio también usa dialog; fila sin incidencia no crea enlace de incidencia', async () => {
    const data = dashboardData()
    data.ultimos_movimientos = [{ ...movement, tipo_incidencia_secuencia: null }]
    await mount('/', 'SUPERADMIN', {}, { '/consultas/dashboard': () => response(data) })
    await settled('Persona del movimiento')
    click(document.querySelector('main button[aria-haspopup=dialog]'))
    expect(document.querySelector('dialog a')).toBeNull()
    click(document.querySelector('dialog button'))
    expect(document.querySelector('dialog')).toBeNull()
  })
  it.each(['SUPERADMIN', 'ADMINISTRADOR'])('Alertas %s va directo a incidencia y devuelve filtros/página sin modal intermedio', async (role) => {
    const { fetcher } = await mount('/eventos-acceso/alertas', role, {
      '/eventos-acceso/alertas': () => response({ alertas: Array.from({ length: 20 }, () => movement) }),
    })
    await settled('Persona del movimiento')
    document.querySelector('#filtro-tipo_movimiento').value = 'SALIDA'
    submit(document.querySelector('main form')); await settled('Persona del movimiento')
    click(findButton('Siguiente')); await settled('Página 2')
    const action = document.querySelector('main a[aria-label^="Ver detalles de incidencia"]')
    click(action)
    expect(location.pathname).toBe('/eventos-acceso/incidencias/9')
    expect(document.querySelector('dialog')).toBeNull()
    await settled('DOCUMENTO-SOLO-INCIDENCIA')
    click(document.querySelector('main .back-link')); await settled('Página 2')
    expect(document.querySelector('#filtro-tipo_movimiento').value).toBe('SALIDA')
    expect(fetcher.mock.calls.at(-1)[0]).toContain('desplazamiento=20')
  })
  it('historial filtra días Bogotá con hasta exclusivo sin reloj de navegador', async () => {
    const { fetcher } = await mount('/eventos-acceso/historial')
    await settled('Persona del movimiento')
    document.querySelector('#filtro-desde').value = '2026-11-17'
    document.querySelector('#filtro-hasta').value = '2026-11-17'
    submit(document.querySelector('main form'))
    await vi.waitFor(() => expect(fetcher.mock.calls.some(([u]) =>
      u.includes('desde=2026-11-17T05%3A00%3A00.000Z') && u.includes('hasta=2026-11-18T05%3A00%3A00.000Z'))).toBe(true))
    expect(findButton('Actualizar historial')).toBeUndefined()
  })
  it('O historial poblado reducido y alertas agregadas, sin filtros o ficha administrativa', async () => {
    const { app } = await mount('/eventos-acceso/historial', 'OPERADOR')
    await settled('SALIDA')
    expect(document.querySelector('main table').querySelectorAll('thead th')).toHaveLength(3)
    expect(document.querySelector('main form,main [aria-haspopup=dialog]')).toBeNull()
    expect(document.querySelector('main').textContent).not.toContain('actor-ficticio')
    app.router.navigate('/eventos-acceso/alertas')
    await settled('Entrada repetida')
    expect(document.querySelector('main table,main form')).toBeNull()
    expect(document.querySelector('main').textContent).toContain('4')
  })
  it('O rechaza historial enriquecido y no monta detalle por URL directa', async () => {
    const { app, fetcher } = await mount('/eventos-acceso/historial', 'OPERADOR', {
      '/eventos-acceso/historial': () => response({ eventos: [movement] }),
    })
    await settled('proyección reducida')
    expect(document.querySelector('main').textContent).not.toContain('actor-ficticio')
    app.router.navigate('/eventos-acceso/incidencias/9')
    expect(document.querySelector('main').textContent).toContain('Acceso no permitido')
    expect(fetcher.mock.calls.some(([u]) => u.includes('/incidencias/'))).toBe(false)
  })
  it.each([400, 403, 404, 503])('detalle/incidencia comunica HTTP %s sin tabla vacía ni éxito inventado', async (status) => {
    await mount('/eventos-acceso/incidencias/9', 'SUPERADMIN', {
      '/eventos-acceso/incidencias/9': () => response({ error: 'Incidencia no disponible ' + status }, status),
    })
    await vi.waitFor(() => expect(document.body.textContent).toContain('Incidencia no disponible ' + status))
    expect(document.querySelector('main dl')).toBeNull()
  })
  it('al salir se aborta lectura; respuesta vieja de otra ruta no aparece', async () => {
    const later = deferred()
    const { app } = await mount('/personas', 'SUPERADMIN', { '/personas': () => later.promise })
    app.router.navigate('/puntos-acceso'); await settled('P-FICTICIO')
    later.resolve(response({ personas: [person] }))
    await Promise.resolve(); await Promise.resolve()
    expect(document.querySelector('main').textContent).not.toContain('DOC-FICTICIO')
  })
  it('cambiar identidad/rol limpia modal, snapshot y filas anteriores', async () => {
    const { app, api } = await mount('/eventos-acceso/historial')
    await settled('Persona del movimiento')
    click(document.querySelector('main button[aria-haspopup=dialog]'))
    api.me = async () => identity('OPERADOR', 2)
    await app.session.refresh()
    await vi.waitFor(() => expect(document.querySelector('main').textContent).toContain('proyección reducida'))
    expect(document.querySelector('dialog')).toBeNull()
    expect(document.body.textContent).not.toContain('Persona del movimiento')
  })
  it('lectura anterior a cambio de cuenta no repuebla dashboard aunque resuelva tarde', async () => {
    const later = deferred()
    const { app, api } = await mount('/', 'SUPERADMIN', {}, { '/consultas/dashboard': () => later.promise })
    api.me = async () => identity('OPERADOR', 2)
    await app.session.refresh()
    later.resolve(response(dashboardData()))
    await vi.waitFor(() => expect(app.dashboard.getState().status).toBe('error'))
    expect(app.dashboard.getState().data).toBeNull()
    expect(document.body.textContent).not.toContain('Personas dentro')
  })
  it('atrás/adelante conserva el ciclo de montaje y foco sin listeners duplicados', async () => {
    const { app, fetcher } = await mount('/puntos-acceso')
    await settled('P-FICTICIO')
    app.router.navigate('/dispositivos-edge'); await settled('D-FICTICIO')
    history.back()
    await vi.waitFor(() => expect(location.pathname).toBe('/puntos-acceso'))
    await settled('P-FICTICIO')
    expect(document.activeElement).toBe(document.querySelector('main'))
    history.forward()
    await vi.waitFor(() => expect(location.pathname).toBe('/dispositivos-edge'))
    await settled('D-FICTICIO')
    expect(fetcher.mock.calls.filter(([u]) => u.startsWith('/api/v1/dispositivos-edge?'))).toHaveLength(2)
  })
  it.each(['/personas/0', '/usuarios/invalido', '/puntos-acceso/-1', '/dispositivos-edge/abc', '/eventos-acceso/incidencias/0'])('ID inválido %s no genera GET de detalle', async (path) => {
    const { fetcher } = await mount(path)
    await settled('identificador')
    expect(fetcher.mock.calls.every(([u]) => u.includes('/auth/') || u.endsWith('/consultas/dashboard'))).toBe(true)
  })
  it('destruir una app pendiente retira listeners/suscripciones y no aplica respuesta posterior', async () => {
    const later = deferred()
    const { app, host, fetcher } = await mount('/puntos-acceso', 'SUPERADMIN', { '/puntos-acceso': () => later.promise })
    app.destroy()
    later.resolve(response({ puntos: [point] }))
    window.dispatchEvent(new PopStateEvent('popstate'))
    await Promise.resolve(); await Promise.resolve()
    expect(host.childNodes).toHaveLength(0)
    expect(app.session.getState().user).toBeNull()
    expect(fetcher.mock.calls.filter(([u]) => u.startsWith('/api/v1/puntos-acceso?'))).toHaveLength(1)
  })
  it.each(['ADMINISTRADOR', 'OPERADOR'])('lecturas IAM denegadas sin consultas para %s', async (role) => {
    const { app, fetcher } = await mount('/usuarios/7', role)
    expect(document.querySelector('main').textContent).toContain('Acceso no permitido')
    app.router.navigate('/usuarios')
    expect(document.querySelector('main').textContent).toContain('Acceso no permitido')
    expect(fetcher.mock.calls.some(([u]) => u.includes('/iam/'))).toBe(false)
  })
  it('O consulta Punto y Dispositivo por URL directa, sin formularios o cambio de estado/modo', async () => {
    const { app, fetcher } = await mount('/puntos-acceso/7', 'OPERADOR')
    await settled('P-FICTICIO')
    app.router.navigate('/dispositivos-edge/7'); await settled('AUTOMATICO')
    expect(document.querySelector('main').textContent).toContain('INACTIVO')
    expect(document.querySelector('main form,main select')).toBeNull()
    expect(fetcher.mock.calls.every(([, options]) => options.method === 'GET')).toBe(true)
  })
  it.each([0, 150])('campana conserva dato válido %s y muestra cifra real en nombre accesible', async (count) => {
    const data = dashboardData(); data.incidencias_hoy = count
    await mount('/', 'SUPERADMIN', {}, { '/consultas/dashboard': () => response(data) })
    await settled('Entradas de hoy')
    const bell = document.querySelector('.header-alerts')
    expect(bell.getAttribute('aria-label')).toContain(count + ' incidencias')
    expect(bell.querySelector('strong').textContent).toBe(count > 99 ? '99+' : String(count))
  })
  it('contexto de filtros de otra cuenta no se restaura al volver a Historial', async () => {
    const { app, fetcher } = await mount('/puntos-acceso')
    await settled('P-FICTICIO')
    app.router.navigate('/eventos-acceso/historial', { state: {
      owner: '999:SUPERADMIN', accessContext: { filters: { id_persona: '123' }, offset: 20 },
    } })
    await settled('Persona del movimiento')
    expect(document.querySelector('#filtro-id_persona').value).toBe('')
    expect(fetcher.mock.calls.at(-1)[0]).toContain('desplazamiento=0')
    expect(fetcher.mock.calls.at(-1)[0]).not.toContain('id_persona=123')
  })
  it('categoría de incidencia desconocida no se convierte en un conteo vacío para O', async () => {
    await mount('/eventos-acceso/alertas', 'OPERADOR', {
      '/eventos-acceso/alertas': () => response({ conteos_por_incidencia: { DESCONOCIDA: 2 } }),
    })
    await settled('categorías de incidencia no reconocidas')
    expect(document.querySelector('main').textContent).not.toContain('No hay incidencias')
  })
  it.each(routes.filter((r) => ['manual', 'personCreate', 'personEdit', 'create'].includes(r.page)).flatMap((route) =>
    ['SUPERADMIN', 'ADMINISTRADOR', 'OPERADOR'].map((role) => [route.path.replace(':id', '7'), role, route.permission])))('ruta pendiente %s con %s mantiene permisos y no ejecuta negocio', async (path, role, permission) => {
    const { fetcher } = await mount(path, role)
    const allowed = permission === 'all' || permission === 'admin' && role !== 'OPERADOR' || permission === 'super' && role === 'SUPERADMIN'
    if (!allowed) expect(document.querySelector('main').textContent).toContain('Acceso no permitido')
    else expect(document.querySelector('main form')).not.toBeNull()
    if (!allowed) expect(document.querySelector('main form')).toBeNull()
    expect(fetcher.mock.calls.every(([, o]) => o.method === 'GET')).toBe(true)
  })
})
