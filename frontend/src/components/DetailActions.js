/** Acciones de ficha y editor administrativo: login, rol y estado son operaciones separadas; SUPERADMIN y eliminación de Persona protegidos. */
import { administrative } from '../auth/permissions.js'
import { field, setOptions, showErrors } from './Fields.js'
import { createWriteFlow } from './writeFlow.js'
import { button, el, link, message } from './dom.js'
import { confirmDialog } from './ConfirmDialog.js'

export function mountDetailActions(ctx, data, onSaved) {
  const { route, params, api, session, navigation, writeRegistry, invalidateReadings } = ctx
  const kind = route.resource, id = params.id
  const user = session.getState().user
  const actions = el('div', { className: 'form-actions', 'aria-label': 'Acciones administrativas' })
  const feedback = el('div', { tabIndex: -1 })
  const editor = el('div')
  const controls = []
  let fields = null, baseline = '', fieldset = null, save = null, active = true, modal = null
  let editingRevision = 0
  const controller = new AbortController()
  const read = () => Object.fromEntries(Object.entries(fields || {}).map(([key, f]) => [key, f.input.value]))
  function lock(locked) {
    for (const control of controls) control.disabled = locked || Boolean(fields)
    if (fieldset) fieldset.disabled = locked
    if (save) save.disabled = locked
  }
  const flow = createWriteFlow({ session, navigation, writeRegistry, invalidateReadings, key: kind + ':' + id,
    feedback, isDirty: () => fields && JSON.stringify(read()) !== baseline, lock })
  const protectedUser = kind === 'users' && data.rol === 'SUPERADMIN'
  if (kind === 'people' && administrative(user)) {
    actions.append(link('/personas/' + id + '/editar', 'Editar Persona', { className: 'btn btn-primary' }),
      el('button', { type: 'button', className: 'btn btn-outline-danger', disabled: true,
        'aria-describedby': 'person-erasure-pending' }, 'Eliminar'))
    feedback.append(el('p', { id: 'person-erasure-pending', className: 'muted' },
      'La eliminación requiere una política aprobada.'))
  }
  if (protectedUser) feedback.append(message('La cuenta SUPERADMIN inicial está protegida.', 'info'))
  function add(text, fn, className = 'btn btn-outline-secondary') {
    const control = button(text, () => { if (flow.getPhase() === 'idle' && !fields) fn(control) }, { className, 'aria-haspopup': 'dialog' })
    controls.push(control); actions.append(control)
  }
  if (!protectedUser && (kind !== 'people' || administrative(user))) {
    add(data.estado === 'ACTIVO' ? 'Desactivar' : 'Activar', (opener) => {
      const value = data.estado === 'ACTIVO' ? 'INACTIVO' : 'ACTIVO'
      void flow.run('Confirmar cambio de estado', kind === 'users' && value === 'INACTIVO'
        ? 'El servidor desactivará la cuenta y revocará sus sesiones. Conserva sus datos e historial.'
        : 'Se cambiará el estado administrativo. No se eliminan datos ni historial; no acciona hardware.',
      () => api[{ people: 'personState', users: 'userState', points: 'pointState', devices: 'deviceState' }[kind]](id, value), onSaved, opener)
    }, data.estado === 'ACTIVO' ? 'btn btn-outline-warning' : 'btn btn-outline-secondary')
  }
  if ((kind === 'points' || kind === 'devices') && administrative(user)) add('Editar', (opener) => edit('datos', opener))
  if (kind === 'devices') add('Cambiar modo', (opener) => edit('modo', opener))
  if (kind === 'users' && !protectedUser) add('Cambiar rol', (opener) => edit('rol', opener))
  if (kind === 'users' && user.rol === 'SUPERADMIN' && !protectedUser) add('Editar usuario', (opener) => edit('login', opener), 'btn btn-primary')
  async function cancelEdit(opener) {
    if (flow.getPhase() !== 'idle') return
    if (JSON.stringify(read()) !== baseline) {
      modal = confirmDialog('¿Descartar cambios?', 'Los cambios del formulario no se guardarán.', document.activeElement, 'Descartar cambios')
      const accepted = await modal.promise; modal = null
      if (!active || !accepted) return
    }
    editingRevision += 1
    fields = null; fieldset = null; save = null; editor.replaceChildren(); lock(false); opener.focus()
  }
  async function edit(type, opener) {
    const revision = ++editingRevision
    fields = {}
    fieldset = el('fieldset', {}, el('legend', {}, 'Editar datos administrativos'))
    const addField = (key, label, options) => {
      fields[key] = field(key, label, { value: data[key], ...options }); fieldset.append(fields[key].node)
    }
    if (type === 'modo') addField('modo_operacion', 'Modo de operación', { options: ['ENTRADA', 'SALIDA', 'AUTOMATICO'].map((value) => ({ value, label: value })) })
    else if (type === 'rol') addField('rol', 'Rol asignable', { options: [] })
    else if (type === 'login') {
      addField('login', 'Usuario', { maxLength: 64, required: true, autocomplete: 'off' })
      fieldset.append(el('p', { className: 'form-help' }, 'De 3 a 64 caracteres: letras sin tildes, números, punto, guion o guion bajo. El rol y el estado se cambian por separado.'))
    }
    else {
      addField('nombre', 'Nombre', { maxLength: 100, required: true })
      if (kind === 'points') addField('descripcion', 'Descripción', { maxLength: 150 })
    }
    baseline = JSON.stringify(read())
    const form = el('form', { className: 'form-panel mt-4', noValidate: true, 'aria-label': 'Editar registro administrativo' })
    save = el('button', { type: 'submit', className: 'btn btn-primary' }, 'Guardar cambios')
    form.append(fieldset, el('div', { className: 'form-actions' }, save, button('Cancelar edición', () => { void cancelEdit(opener) })))
    editor.replaceChildren(form); lock(false)
    let roles = []
    if (type === 'rol') {
      try {
        const catalog = await api.roles(controller.signal)
        if (!active || revision !== editingRevision) return
        roles = (catalog?.roles || []).filter((r) => r.asignable && ['ADMINISTRADOR', 'OPERADOR'].includes(r.nombre))
        setOptions(fields.rol.input, roles.map((r) => ({ value: r.nombre, label: r.nombre })), data.rol)
        baseline = JSON.stringify(read())
      } catch {
        if (active && revision === editingRevision) feedback.replaceChildren(message('No se pudo consultar el catálogo de roles.'))
      }
    }
    if (!active || revision !== editingRevision) return
    Object.values(fields)[0].input.focus()
    form.addEventListener('submit', (event) => {
      event.preventDefault()
      if (flow.getPhase() !== 'idle') return
      const values = read(), errors = {}
      if (fields.login && !/^[a-z0-9][a-z0-9._-]{2,63}$/.test(values.login.trim().toLowerCase())) errors.login = 'Usuario no válido: entre 3 y 64 caracteres permitidos.'
      if (fields.nombre && (!values.nombre.trim() || values.nombre.trim().length > 100 || [...values.nombre].some((c) => c.charCodeAt(0) < 32))) errors.nombre = 'Nombre obligatorio, máximo 100 caracteres sin controles.'
      if (fields.descripcion && (values.descripcion.length > 150 || [...values.descripcion].some((c) => c.charCodeAt(0) < 32))) errors.descripcion = 'Descripción no válida.'
      if (fields.rol && !roles.some((r) => r.nombre === values.rol)) errors.rol = 'Selecciona un rol asignable.'
      if (fields.modo_operacion && !['ENTRADA', 'SALIDA', 'AUTOMATICO'].includes(values.modo_operacion)) errors.modo_operacion = 'Selecciona un modo válido.'
      showErrors(fields, errors)
      if (Object.keys(errors).length) return
      const changes = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, (key === 'login' ? value.trim().toLowerCase() : value.trim()) || null])
        .filter(([key, value]) => value !== (data[key] || null)))
      if (!Object.keys(changes).length) { feedback.replaceChildren(message('No hay cambios para guardar.', 'info')); return }
      const operation = () => type === 'modo' ? api.deviceMode(id, changes.modo_operacion)
        : type === 'login' ? api.userLogin(id, changes.login).catch((error) => {
          if (active && error.status === 409) showErrors(fields, { login: 'Este usuario ya existe. Elige otro identificador.' })
          throw error
        })
        : type === 'rol' ? api.userRole(id, changes.rol)
          : kind === 'points' ? api.updatePoint(id, changes) : api.updateDevice(id, changes.nombre)
      void flow.run('Confirmar edición', 'Se guardarán únicamente los datos administrativos modificados; se conserva el historial.', operation, onSaved, save)
    })
  }
  if (flow.getPhase() === 'uncertain') lock(true)
  return { actions, node: el('div', {}, feedback, editor),
    destroy: () => { active = false; controller.abort(); flow.destroy(); modal?.destroy(); actions.remove(); editor.remove() } }
}
