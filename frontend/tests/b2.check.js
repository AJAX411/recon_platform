import { afterEach, describe, expect, it, vi } from 'vitest'
import { businessApp, dialogButton, input, manualResponse, submit, waitText, writes } from './businessHelpers.js'
import { click, deferred, findButton, identity, response } from './helpers.js'

const cleanups=[]
afterEach(()=>{while(cleanups.length)cleanups.pop()()})
async function mount(role='SUPERADMIN',overrides={}) {
  const app=await businessApp('/eventos-acceso/manual',role,overrides);cleanups.push(app.stop);return app
}
const body={id_persona:7,id_punto_acceso:8,tipo_movimiento:'ENTRADA'}
const manualWrites=(fetcher)=>writes(fetcher).filter(([url])=>url.endsWith('/eventos-acceso/manual'))
async function select(type='ENTRADA') {
  await vi.waitFor(()=>expect(document.querySelector('#id_punto_acceso').options.length).toBe(2))
  input('persona_valor','Persona');click(findButton('Buscar Persona'))
  await vi.waitFor(()=>expect(document.querySelector('#persona_elegida').options.length).toBe(2))
  expect(document.querySelector('#persona_elegida').value).toBe('')
  input('persona_elegida','7');input('id_punto_acceso','8');input('tipo_movimiento_manual',type)
}
async function send(type='ENTRADA') {await select(type);submit();click(dialogButton('Confirmar registro'))}
async function allowNavigation(app,url) {
  app.router.navigate(url)
  click(dialogButton('Continuar y salir'))
  await vi.waitFor(()=>expect(location.pathname).toBe(url))
}

describe('B2 · declaración manual',()=>{
  it.each(['SUPERADMIN','ADMINISTRADOR','OPERADOR'])('flujo %s tiene un form vertical, selección explícita, Punto activo y POST solo tras confirmar',async(role)=>{
    const {fetcher,state}=await mount(role)
    expect(document.querySelectorAll('main form')).toHaveLength(1)
    expect(document.querySelector('form form')).toBeNull()
    submit();expect(document.querySelector('dialog')).toBeNull()
    await select('SALIDA')
    expect([...document.querySelector('#id_punto_acceso').options].some((o)=>o.value==='7')).toBe(false)
    submit();expect(manualWrites(fetcher)).toHaveLength(0)
    expect(document.querySelector('dialog').textContent).toContain('Persona Ficticia')
    click(dialogButton('Confirmar registro'));await waitText('Declaración registrada')
    expect(manualWrites(fetcher)).toHaveLength(1)
    const options=manualWrites(fetcher)[0][1]
    expect(JSON.parse(options.body)).toEqual({...body,tipo_movimiento:'SALIDA'})
    expect(options.headers['Idempotency-Key']).toMatch(/^[0-9a-f-]{36}$/)
    expect(state.declarations.size).toBe(1)
    expect(document.querySelector('main').textContent).toContain('No equivale a denegación automática')
  })
  it.each(['cancel','escape','x'])('confirmación %s no registra ni genera una declaración',async(how)=>{
    const {app,fetcher}=await mount();await select();submit()
    const dialog=document.querySelector('dialog')
    if(how==='cancel')click(dialogButton('Cancelar'))
    if(how==='escape')dialog.dispatchEvent(new Event('cancel',{cancelable:true}))
    if(how==='x')click(dialog.querySelector('[aria-label^="Cerrar"]'))
    await vi.waitFor(()=>expect(findButton('Revisar declaración').disabled).toBe(false))
    expect(app.manual.getState()).toBeNull()
    expect(manualWrites(fetcher)).toHaveLength(0)
    expect(document.activeElement).toBe(findButton('Revisar declaración'))
  })
  it('Enter en buscadores y selección vacía jamás envían el movimiento',async()=>{
    const {fetcher}=await mount()
    input('persona_valor','Persona')
    const event=new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true})
    document.querySelector('#persona_valor').dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
    input('codigo_punto','P8')
    const pointEvent=new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true})
    document.querySelector('#codigo_punto').dispatchEvent(pointEvent)
    expect(pointEvent.defaultPrevented).toBe(true)
    await vi.waitFor(()=>expect(document.querySelector('#persona_elegida').options.length).toBe(2))
    submit()
    expect(document.querySelector('dialog')).toBeNull()
    expect(manualWrites(fetcher)).toHaveLength(0)
  })
  it('búsqueda inválida no consulta elegibles y una Persona inactiva no aparece',async()=>{
    const {state,fetcher}=await mount()
    input('persona_valor','ab');click(findButton('Buscar Persona'))
    expect(fetcher.mock.calls.some(([url])=>url.includes('personas-elegibles'))).toBe(false)
    state.people[7].estado='INACTIVO'
    input('persona_valor','Persona');click(findButton('Buscar Persona'))
    await waitText('No hay Personas activas')
    expect(document.querySelector('#persona_elegida').options.length).toBe(1)
  })
  it('una búsqueda nueva invalida selección de Persona y respuesta anterior',async()=>{
    const later=deferred();let requests=0
    await mount('SUPERADMIN',{'/eventos-acceso/personas-elegibles':()=>++requests===1?later.promise:response({personas:[]})})
    input('persona_valor','Antigua');click(findButton('Buscar Persona'))
    input('persona_valor','Nueva');click(findButton('Buscar Persona'))
    await waitText('No hay Personas activas')
    later.resolve(response({personas:[{id_persona:7,nombre:'NO-MOSTRAR-ANTERIOR'}]}))
    await Promise.resolve();await Promise.resolve()
    expect(document.body.textContent).not.toContain('NO-MOSTRAR-ANTERIOR')
  })
  it('doble confirmación/submit y retry durante envío mantienen una única escritura',async()=>{
    const later=deferred()
    const {app,fetcher}=await mount('SUPERADMIN',{'/eventos-acceso/manual':()=>later.promise})
    await select();submit()
    const confirm=dialogButton('Confirmar registro');click(confirm);click(confirm)
    await vi.waitFor(()=>expect(manualWrites(fetcher)).toHaveLength(1))
    expect(app.manual.start(body)).toBe(false);expect(app.manual.retry()).toBe(false)
    expect(Object.isFrozen(app.manual.getState().body)).toBe(true)
    later.resolve(response(manualResponse(),201));await waitText('Declaración registrada')
  })
  it('201 confirmado invalida dashboard; un GET posterior fallido no repite POST',async()=>{
    const {app,fetcher}=await mount('SUPERADMIN',{'/eventos-acceso/historial':()=>response({error:'Lectura caída'},503)})
    await send();await waitText('Declaración registrada')
    await vi.waitFor(()=>expect(fetcher.mock.calls.filter(([url])=>url.endsWith('/consultas/dashboard')).length).toBe(2))
    app.router.navigate('/eventos-acceso/historial');await waitText('Lectura caída')
    click(findButton('Reintentar consulta'));await waitText('Lectura caída')
    app.router.navigate('/')
    await waitText('Entradas de hoy')
    expect(manualWrites(fetcher)).toHaveLength(1)
  })
  it('retry explícito de respuesta perdida conserva clave/cuerpo/actor y recupera replay sin duplicar evento ficticio',async()=>{
    let count=0
    const {app,fetcher,state}=await mount('SUPERADMIN',{'/eventos-acceso/manual':(_url,options,s)=>{
      const data=manualResponse(JSON.parse(options.body)),key=options.headers['Idempotency-Key']
      if(++count===1){s.declarations.set(key,data);return Promise.reject(new Error('Respuesta perdida'))}
      return response(s.declarations.get(key),200,{'Idempotent-Replay':'true'})
    }})
    await send();await waitText('Resultado incierto')
    const before=app.manual.getState(),first=manualWrites(fetcher)[0][1]
    await Promise.resolve();expect(manualWrites(fetcher)).toHaveLength(1)
    click(findButton('Reintentar la misma declaración'));await waitText('Declaración ya registrada')
    const second=manualWrites(fetcher)[1][1]
    expect(second.body).toBe(first.body)
    expect(second.headers['Idempotency-Key']).toBe(before.key)
    expect(app.manual.getState().actorId).toBe(before.actorId)
    expect(state.declarations.size).toBe(1)
  })
  it('preflight CSRF no enviado permite retry con la misma clave, sin POST inicial',async()=>{
    let count=0
    const {app,fetcher}=await mount('SUPERADMIN',{'/auth/csrf':()=>++count===1?response({error:'CSRF caído'},503):response({csrf_token:'csrf-ficticio'})})
    await send();await waitText('No se envió la declaración')
    const key=app.manual.getState().key
    expect(manualWrites(fetcher)).toHaveLength(0)
    click(findButton('Reintentar la misma declaración'));await waitText('Declaración registrada')
    expect(manualWrites(fetcher)).toHaveLength(1)
    expect(manualWrites(fetcher)[0][1].headers['Idempotency-Key']).toBe(key)
  })
  it.each([400,404,409,429])('HTTP %s no se reintenta automáticamente ni rota clave',async(status)=>{
    const {app,fetcher}=await mount('SUPERADMIN',{'/eventos-acceso/manual':()=>response({error:'Rechazo '+status},status)})
    await send();await waitText('No se confirmó el registro')
    const snapshot=app.manual.getState()
    expect(snapshot.phase).toBe(status===409?'conflict':'rejected')
    expect(findButton('Reintentar la misma declaración')).toBeUndefined()
    expect(manualWrites(fetcher)).toHaveLength(1)
    expect(app.manual.getState().key).toBe(snapshot.key)
    expect(document.querySelector('main').textContent).not.toContain('Declaración registrada')
  })
  it.each([401,403])('HTTP %s expira/niega sesión sin reenviar ni exponer intento',async(status)=>{
    const {app,fetcher}=await mount('SUPERADMIN',{'/eventos-acceso/manual':()=>response({error:'Permiso perdido'},status)})
    await send()
    await vi.waitFor(()=>expect(app.session.getState().user).toBeNull())
    expect(app.manual.getState()).toBeNull()
    expect(manualWrites(fetcher)).toHaveLength(1)
    expect(document.querySelector('#persona_elegida')).toBeNull()
  })
  it.each(['503','network','invalidId','wrongActor','wrongBody','wrongResult','missingReplay','badTime'])('resultado %s permanece incierto y no permite empezar otra declaración',async(kind)=>{
    const {app,fetcher}=await mount('SUPERADMIN',{'/eventos-acceso/manual':()=>{
      if(kind==='503')return response({error:'Temporal'},503)
      if(kind==='network')return Promise.reject(new Error('Caída'))
      const data=manualResponse()
      if(kind==='invalidId')data.id_evento_acceso=null
      if(kind==='wrongActor')data.id_usuario_registrador=99
      if(kind==='wrongBody')data.id_persona=99
      if(kind==='wrongResult')data.resultado='RECHAZADO'
      if(kind==='badTime')data.fecha_hora_ocurrencia='2026-11-17'
      return response(data,kind==='missingReplay'?200:201)
    }})
    await send();await waitText('Resultado incierto')
    expect(app.manual.getState().phase).toBe('uncertain')
    expect(app.manual.start(body)).toBe(false)
    expect(app.manual.clear({confirmed:true})).toBe(false)
    expect(findButton('Cerrar solicitud y revisar formulario')).toBeUndefined()
    expect(manualWrites(fetcher)).toHaveLength(1)
  })
  it('intento incierto sobrevive a navegación confirmada y se advierte antes de recarga',async()=>{
    const {app,fetcher}=await mount('SUPERADMIN',{'/eventos-acceso/manual':()=>response({error:'Temporal'},503)})
    await send();await waitText('Resultado incierto')
    const snapshot=app.manual.getState()
    const unload=new Event('beforeunload',{cancelable:true});window.dispatchEvent(unload);expect(unload.defaultPrevented).toBe(true)
    app.router.navigate('/')
    click(dialogButton('Cancelar'));await new Promise((resolve)=>setTimeout(resolve,0))
    expect(location.pathname).toBe('/eventos-acceso/manual')
    await allowNavigation(app,'/');await waitText('Entradas de hoy')
    await allowNavigation(app,'/eventos-acceso/manual');await waitText('Resultado incierto')
    expect(app.manual.getState().key).toBe(snapshot.key)
    expect(manualWrites(fetcher)).toHaveLength(1)
  })
  it('logout incierto tiene advertencia; cancelar no revoca y confirmar no elimina la clave en memoria',async()=>{
    const {app,fetcher}=await mount('SUPERADMIN',{'/eventos-acceso/manual':()=>response({error:'Temporal'},503)})
    await send();await waitText('Resultado incierto')
    const key=app.manual.getState().key
    click(findButton('cuenta-ficticia · SUPERADMIN'));click(findButton('Cerrar sesión'));click(dialogButton('Cancelar'))
    await new Promise((resolve)=>setTimeout(resolve,0))
    expect(fetcher.mock.calls.some(([url])=>url.endsWith('/auth/logout'))).toBe(false)
    click(findButton('Cerrar sesión'));click(dialogButton('Continuar y salir'))
    await vi.waitFor(()=>expect(app.session.getState().status).toBe('anonymous'))
    expect(app.manual.getState()).toBeNull()
    app.session.refresh()
    await vi.waitFor(()=>expect(app.session.getState().status).toBe('authenticated'))
    expect(app.manual.getState().key).toBe(key)
    expect(manualWrites(fetcher)).toHaveLength(1)
  })
  it('envío en curso bloquea navegación/logout y no pierde la solicitud',async()=>{
    const later=deferred()
    const {app,fetcher}=await mount('SUPERADMIN',{'/eventos-acceso/manual':()=>later.promise})
    await send();await vi.waitFor(()=>expect(manualWrites(fetcher)).toHaveLength(1))
    app.router.navigate('/');click(dialogButton('Entendido'))
    await new Promise((resolve)=>setTimeout(resolve,0))
    expect(location.pathname).toBe('/eventos-acceso/manual')
    click(findButton('cuenta-ficticia · SUPERADMIN'));click(findButton('Cerrar sesión'));click(dialogButton('Entendido'))
    await new Promise((resolve)=>setTimeout(resolve,0))
    expect(fetcher.mock.calls.some(([url])=>url.endsWith('/auth/logout'))).toBe(false)
    later.resolve(response(manualResponse(),201));await waitText('Declaración registrada')
  })
  it.each([['ADMINISTRADOR',2],['OPERADOR',1]])('otra identidad %s/%s recibe bloqueo sin clave/cuerpo/actor y no envía',async(role,id)=>{
    const {app,api,fetcher}=await mount('SUPERADMIN',{'/eventos-acceso/manual':()=>response({error:'Temporal'},503)})
    await send();await waitText('Resultado incierto')
    const key=app.manual.getState().key
    api.me=async()=>identity(role,id);await app.session.refresh()
    await waitText('bloqueada por cambio de identidad')
    expect(Object.keys(app.manual.getState()).sort()).toEqual(['error','phase'])
    expect(app.manual.start(body)).toBe(false);expect(app.manual.retry()).toBe(false)
    expect(document.body.textContent).not.toContain(key)
    api.me=async()=>identity('SUPERADMIN',1);await app.session.refresh()
    expect(app.manual.getState().key).toBe(key)
    expect(manualWrites(fetcher)).toHaveLength(1)
  })
  it('respuesta antigua después de cambio de identidad no confirma ni se muestra a la nueva cuenta',async()=>{
    const later=deferred()
    const {app,api,fetcher}=await mount('SUPERADMIN',{'/eventos-acceso/manual':()=>later.promise})
    await send();await vi.waitFor(()=>expect(manualWrites(fetcher)).toHaveLength(1))
    api.me=async()=>identity('OPERADOR',2);await app.session.refresh()
    later.resolve(response(manualResponse(),201))
    await vi.waitFor(()=>expect(app.manual.getState().phase).toBe('identityBlocked'))
    expect(document.body.textContent).not.toContain('Declaración registrada')
    api.me=async()=>identity();await app.session.refresh()
    await vi.waitFor(()=>expect(app.manual.getState().phase).toBe('uncertain'))
  })
  it('O resultado manual solo proyecta movimiento/resultado/método/hora aproximada, sin IDs ni ficha',async()=>{
    const {app}=await mount('OPERADOR')
    await send('SALIDA');await waitText('Declaración registrada')
    const result=app.manual.getState().response.data
    expect(result.id_evento_acceso).toBeUndefined();expect(result.id_persona).toBeUndefined();expect(result.id_usuario_registrador).toBeUndefined()
    expect(document.querySelector('main').textContent).not.toContain('Referencia interna')
    expect(document.querySelector('main').textContent).not.toContain('Persona Ficticia')
    expect(document.querySelector('main a[href^="/eventos-acceso/incidencias/"]')).toBeNull()
    expect(result.hora_local_aproximada).not.toContain('09:42')
  })
  it('solo tras éxito o cierre explícito de rechazo se permite una nueva clave',async()=>{
    const {app,fetcher}=await mount()
    await send();await waitText('Declaración registrada')
    const firstKey=app.manual.getState().key
    click(findButton('Registrar otra declaración'))
    await select('SALIDA');submit();click(dialogButton('Confirmar registro'));await waitText('Declaración registrada')
    expect(app.manual.getState().key).not.toBe(firstKey)
    expect(manualWrites(fetcher)).toHaveLength(2)
  })
  it('409 requiere cerrar explícitamente; cancelar cierre conserva la clave y no permite retry',async()=>{
    let count=0
    const {app,fetcher}=await mount('SUPERADMIN',{'/eventos-acceso/manual':()=>++count===1?response({error:'Conflicto'},409):undefined})
    await send();await waitText('Conflicto 409')
    const key=app.manual.getState().key
    expect(app.manual.clear()).toBe(false)
    click(findButton('Cerrar solicitud y revisar formulario'));click(dialogButton('Cancelar'))
    await new Promise((resolve)=>setTimeout(resolve,0))
    expect(app.manual.getState().key).toBe(key)
    click(findButton('Cerrar solicitud y revisar formulario'));click(dialogButton('Cerrar solicitud'))
    await vi.waitFor(()=>expect(document.querySelector('main form')).not.toBeNull())
    await send();await waitText('Declaración registrada')
    expect(app.manual.getState().key).not.toBe(key)
    expect(manualWrites(fetcher)).toHaveLength(2)
  })
  it('solo Personas ACTIVO y Punto ACTIVO se usan en manual; cambio concurrente se rechaza sin simular éxito',async()=>{
    const {state,app}=await mount()
    await select()
    submit()
    // El cambio ocurre después de la revisión cliente y antes de la escritura.
    state.points[8].estado='INACTIVO'
    click(dialogButton('Confirmar registro'))
    await waitText('Referencia no disponible')
    expect(app.manual.getState().phase).toBe('rejected')
    expect(state.declarations.size).toBe(0)
  })
  it('después de confirmar se releen Historial y Alertas al visitarlos; O conserva proyección reducida',async()=>{
    const {app,fetcher}=await mount('OPERADOR')
    await send('SALIDA');await waitText('Declaración registrada')
    app.router.navigate('/eventos-acceso/historial');await waitText('SALIDA')
    expect(document.querySelector('main table').querySelectorAll('thead th')).toHaveLength(3)
    expect(document.querySelector('main').textContent).not.toContain('cuenta-ficticia')
    app.router.navigate('/eventos-acceso/alertas');await waitText('Salida sin entrada de la jornada')
    expect(document.querySelector('main table')).toBeNull()
    expect(manualWrites(fetcher)).toHaveLength(1)
  })
  it('borrador manual no confirmado pregunta antes de salir y antes de recargar',async()=>{
    const {app,fetcher}=await mount()
    input('persona_valor','Borrador')
    const unload=new Event('beforeunload',{cancelable:true});window.dispatchEvent(unload)
    expect(unload.defaultPrevented).toBe(true)
    app.router.navigate('/')
    expect(document.querySelector('dialog').textContent).toContain('sin confirmar')
    click(dialogButton('Cancelar'));await new Promise((resolve)=>setTimeout(resolve,0))
    expect(document.querySelector('#persona_valor').value).toBe('Borrador')
    expect(manualWrites(fetcher)).toHaveLength(0)
  })
  it('UUID no disponible es fallo local, sin POST ni persistencia de claves',async()=>{
    const {app,fetcher}=await mount()
    vi.spyOn(crypto,'randomUUID').mockImplementation(()=>{throw new Error('No disponible')})
    expect(app.manual.start(body)).toBe(false)
    expect(app.manual.getState().phase).toBe('localError')
    expect(manualWrites(fetcher)).toHaveLength(0)
    expect(localStorage.length).toBe(0);expect(sessionStorage.length).toBe(0)
  })
  it('si UUID falla después de abrir revisión, la UI informa fallo local y permite cerrar sin POST',async()=>{
    const {app,fetcher}=await mount()
    await select()
    vi.spyOn(crypto,'randomUUID').mockImplementation(()=>{throw new Error('No disponible')})
    submit();click(dialogButton('Confirmar registro'))
    await waitText('No se pudo crear una clave segura')
    expect(app.manual.getState().phase).toBe('localError')
    click(findButton('Cerrar solicitud y revisar formulario'));click(dialogButton('Cerrar solicitud'))
    await vi.waitFor(()=>expect(document.querySelector('main form')).not.toBeNull())
    expect(manualWrites(fetcher)).toHaveLength(0)
  })
})
