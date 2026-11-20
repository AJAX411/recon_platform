import { field, setOptions, showErrors } from '../components/Fields.js'
import { createWriteFlow } from '../components/writeFlow.js'
import { mountPointSelector } from '../components/PointSelector.js'
import { button, el, loading, message, page } from '../components/dom.js'

const MODES = ['ENTRADA', 'SALIDA', 'AUTOMATICO']
const invalidText = (value, max) => !value.trim() || value.trim().length > max || [...value].some((c) => c.charCodeAt(0) < 32)
export function mountCreateResource(ctx) {
  const { container, route, api, session, navigation, writeRegistry, invalidateReadings, navigate } = ctx
  const kind = route.resource
  const isUser = kind === 'users', isDevice = kind === 'devices'
  const fields = {}
  const group = el('fieldset', {}, el('legend', {}, isUser ? 'Datos de acceso' : 'Datos administrativos'))
  function add(key, label, options) { fields[key] = field(key, label, options); group.append(fields[key].node) }
  if (isUser) {
    add('login', 'Usuario', { maxLength: 64, autocomplete: 'off', required: true })
    add('rol', 'Rol', { options: [], required: true })
    add('contrasena', 'Contraseña inicial', { type: 'password', minLength: 12, maxLength: 1024, autocomplete: 'new-password', required: true })
  } else {
    add('codigo', 'Código', { maxLength: 20, required: true })
    add('nombre', 'Nombre', { maxLength: 100, required: true })
    if (isDevice) add('modo_operacion', 'Modo de operación', { options: MODES.map((value) => ({ value, label: value })), required: true })
    else add('descripcion', 'Descripción', { maxLength: 150 })
  }
  const selector = isDevice ? mountPointSelector({ api, activeOnly: false, label: 'Punto de Acceso existente', showCodeFilter: false }) : null
  if (selector) group.append(selector.node)
  const title = isUser ? 'Crear cuenta' : isDevice ? 'Registrar dispositivo' : 'Crear Punto de Acceso'
  const view = page(title, isUser ? 'Solo SUPERADMIN administra cuentas, independientes de Persona.'
    : isDevice ? 'Metadatos administrativos; no establece conexión física.' : 'El estado no acciona una puerta.')
  const feedback = el('div', { tabIndex: -1 }), catalogFeedback = el('div')
  const form = el('form', { noValidate: true, className: 'form-panel', 'aria-label': title })
  const save = el('button', { type: 'submit', className: 'btn btn-primary', 'aria-haspopup': 'dialog' }, title)
  const root = isUser ? '/usuarios' : isDevice ? '/dispositivos-edge' : '/puntos-acceso'
  const read = () => ({ ...Object.fromEntries(Object.entries(fields).map(([key, f]) => [key, f.input.value])),
    ...(selector ? { id_punto_acceso: selector.getSelected()?.id_punto_acceso || null } : {}) })
  const baseline = JSON.stringify(read())
  let active = true, roles = []
  const controller = new AbortController()
  const flow = createWriteFlow({ session, navigation, writeRegistry, invalidateReadings, key: kind + ':create', feedback, secret: isUser,
    isDirty: () => JSON.stringify(read()) !== baseline,
    lock: (locked) => { group.disabled = locked; save.disabled = locked } })
  form.append(group, el('div', { className: 'form-actions' }, save, button('Cancelar', () => navigate(root))))
  view.append(feedback, catalogFeedback, form); container.replaceChildren(view)
  async function loadRoles() {
    catalogFeedback.replaceChildren(loading())
    try {
      const data = await api.roles(controller.signal)
      if (!active || controller.signal.aborted) return
      if (!Array.isArray(data?.roles)) throw new Error('Catálogo de roles no disponible.')
      roles = data.roles.filter((r) => r.asignable && ['ADMINISTRADOR', 'OPERADOR'].includes(r.nombre))
      setOptions(fields.rol.input, roles.map((r) => ({ value: r.nombre, label: r.nombre })))
      catalogFeedback.replaceChildren(...(roles.length ? [] : [message('No hay roles asignables.', 'warning')]))
    } catch {
      if (active && !controller.signal.aborted) catalogFeedback.replaceChildren(message('Catálogo de roles no disponible.'), button('Reintentar roles', loadRoles))
    }
  }
  if (isUser) void loadRoles()
  form.addEventListener('submit', (event) => {
    event.preventDefault()
    if (flow.getPhase() !== 'idle') return
    const values = read(), errors = {}
    if (isUser) {
      if (!/^[a-z0-9][a-z0-9._-]{2,63}$/i.test(values.login.trim())) errors.login = 'Usa de 3 a 64 caracteres admitidos en un usuario.'
      if (values.contrasena.length < 12 || values.contrasena.length > 1024) errors.contrasena = 'La contraseña requiere entre 12 y 1024 caracteres.'
      if (!roles.some((r) => r.nombre === values.rol)) errors.rol = 'Selecciona un rol asignable.'
    } else {
      if (invalidText(values.codigo, 20)) errors.codigo = 'Código obligatorio, máximo 20 caracteres sin controles.'
      if (invalidText(values.nombre, 100)) errors.nombre = 'Nombre obligatorio, máximo 100 caracteres sin controles.'
      if (isDevice && !MODES.includes(values.modo_operacion)) errors.modo_operacion = 'Selecciona un modo válido.'
      if (!isDevice && values.descripcion && (values.descripcion.trim().length > 150 || [...values.descripcion].some((c) => c.charCodeAt(0) < 32))) errors.descripcion = 'Descripción no válida.'
      if (isDevice && !values.id_punto_acceso) errors.id_punto_acceso = 'Selecciona explícitamente un Punto existente.'
    }
    showErrors(fields, errors)
    if (Object.keys(errors).length) {
      if (errors.id_punto_acceso) { feedback.replaceChildren(message(errors.id_punto_acceso)); selector.select.focus() }
      return
    }
    const body = isUser ? { login: values.login.trim(), contrasena: values.contrasena, rol: values.rol }
      : isDevice ? { codigo: values.codigo.trim(), nombre: values.nombre.trim(), modo_operacion: values.modo_operacion, id_punto_acceso: values.id_punto_acceso }
        : { codigo: values.codigo.trim(), nombre: values.nombre.trim(), descripcion: values.descripcion.trim() || null }
    const operation = () => api[isUser ? 'createUser' : isDevice ? 'createDevice' : 'createPoint'](body)
    void flow.run('Confirmar ' + title.toLowerCase(), isUser ? 'Se creará una cuenta con el rol seleccionado. La contraseña no se muestra.'
      : 'Se guardará el registro administrativo. No acredita conexión física.', operation,
    (saved) => navigate(root + '/' + saved[isUser ? 'id_usuario' : isDevice ? 'id_dispositivo' : 'id_punto_acceso'], { replace: true }), save)
      .finally(() => { if (isUser) fields.contrasena.input.value = '' })
  })
  return () => { active = false; controller.abort(); flow.destroy(); selector?.destroy(); if (isUser) fields.contrasena.input.value = ''; view.remove() }
}
