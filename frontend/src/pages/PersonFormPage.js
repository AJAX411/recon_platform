/** Alta/edición de Persona: ocho campos administrativos, catálogos reales y confirmación de valores o cambios antes de enviar. */
import { PERSON_FIELDS, initialPersonValues, personPayload, changedPersonFields, validatePerson } from '../people/personForm.js'
import { field, setOptions, showErrors } from '../components/Fields.js'
import { createWriteFlow } from '../components/writeFlow.js'
import { button, dataGrid, el, link, loading, message, page } from '../components/dom.js'

export function mountPersonForm(ctx) {
  const { container, params, route, api, session, navigation, navigate, writeRegistry, invalidateReadings } = ctx
  const editing = route.page === 'personEdit'
  const view = page(editing ? 'Editar Persona' : 'Registrar Persona', 'Registro administrativo independiente de una cuenta web.')
  const feedback = el('div', { tabIndex: -1 })
  const catalogs = el('div')
  const form = el('form', { noValidate: true, 'aria-label': editing ? 'Editar datos de Persona' : 'Registrar datos de Persona', className: 'form-panel person-form' })
  const group = el('fieldset', {}, el('legend', {}, 'Datos administrativos de Persona'))
  const fields = {}
  for (const [key, spec] of Object.entries(PERSON_FIELDS)) {
    fields[key] = field(key, spec.label, { maxLength: spec.max, required: spec.required,
      ...(['tipo_persona', 'tipo_documento'].includes(key) ? { options: [] } : {}) })
    group.append(fields[key].node)
  }
  const save = el('button', { type: 'submit', className: 'btn btn-primary', 'aria-haspopup': 'dialog' }, editing ? 'Guardar cambios' : 'Registrar Persona')
  const back = editing ? '/personas/' + params.id : '/personas'
  const cancel = button('Cancelar', () => navigate(back))
  form.append(group, el('div', { className: 'form-actions' }, save, cancel))
  view.append(link(back, '← Volver a Personas', { className: 'back-link' }), feedback, catalogs, form)
  container.replaceChildren(view)
  let active = true, previous = null, baseline = '', types = [], documents = [], catalogReady = false, resourceReady = !editing
  let catalogRevision = 0
  const controller = new AbortController()
  const read = () => Object.fromEntries(Object.entries(fields).map(([key, f]) => [key, f.input.value]))
  const flow = createWriteFlow({ session, navigation, writeRegistry, invalidateReadings,
    key: editing ? 'people:' + params.id : 'people:create', feedback,
    isDirty: () => resourceReady && JSON.stringify(read()) !== baseline,
    lock: (locked) => { group.disabled = locked || !resourceReady; save.disabled = locked || !resourceReady } })
  function fill(person) {
    for (const [key, value] of Object.entries(initialPersonValues(person))) {
      if (fields[key].input.tagName === 'SELECT' && value) fields[key].input.append(el('option', { value }, value))
      fields[key].input.value = value
    }
    baseline = JSON.stringify(read())
  }
  fill({})
  async function loadCatalogs() {
    const revision = ++catalogRevision
    catalogReady = false
    catalogs.replaceChildren(loading())
    const results = await Promise.allSettled([api.personTypes(controller.signal), api.documentTypes(controller.signal)])
    if (!active || controller.signal.aborted || revision !== catalogRevision) return
    const old = read()
    types = results[0].status === 'fulfilled' && Array.isArray(results[0].value?.tipos) ? results[0].value.tipos : []
    documents = results[1].status === 'fulfilled' && Array.isArray(results[1].value?.tipos_documento)
      ? results[1].value.tipos_documento.filter((d) => typeof d.codigo === 'string' && typeof d.nombre === 'string' && typeof d.habilitado_para_altas === 'boolean') : []
    catalogReady = results[1].status === 'fulfilled' && Array.isArray(results[1].value?.tipos_documento)
    setOptions(fields.tipo_persona.input, types.filter((t) => t.estado === 'ACTIVO').map((t) => ({ value: t.nombre, label: t.nombre })), old.tipo_persona)
    const options = documents.filter((d) => d.habilitado_para_altas).map((d) => ({ value: d.codigo, label: d.nombre + ' (' + d.codigo + ')' }))
    if (previous?.tipo_documento && !options.some((d) => d.value === previous.tipo_documento)) {
      options.unshift({ value: previous.tipo_documento, label: previous.tipo_documento + ' (valor registrado; conservar número)' })
    }
    setOptions(fields.tipo_documento.input, options, old.tipo_documento)
    if (old.tipo_persona && !types.some((t) => t.estado === 'ACTIVO' && t.nombre === old.tipo_persona)) {
      fields.tipo_persona.input.append(el('option', { value: old.tipo_persona, disabled: true, selected: true }, old.tipo_persona + ' (no disponible)'))
    }
    catalogs.replaceChildren(...(!types.length || !catalogReady || !documents.some((d) => d.habilitado_para_altas)
      ? [message('Catálogo no disponible o sin opciones habilitadas. Se conserva el borrador y el documento histórico; solo se enviarán cambios compatibles.', 'warning'),
        button('Reintentar catálogos', loadCatalogs)] : []))
  }
  async function start() {
    if (editing) {
      group.disabled = true; save.disabled = true
      try {
        previous = await api.person(params.id, controller.signal)
        if (!active) return
        if (String(previous?.id_persona) !== params.id) throw new Error('La respuesta no corresponde a la Persona.')
        resourceReady = true
        fill(previous)
      } catch (error) {
        if (active && !controller.signal.aborted) feedback.replaceChildren(message(error.message))
        return
      }
    }
    await loadCatalogs()
    if (active) {
      group.disabled = flow.getPhase() === 'uncertain'
      save.disabled = flow.getPhase() === 'uncertain'
    }
  }
  form.addEventListener('submit', (event) => {
    event.preventDefault()
    if (!resourceReady || flow.getPhase() !== 'idle') return
    const values = read()
    const errors = validatePerson(values, types, { previous: editing ? previous : undefined, documentTypes: documents, catalogReady })
    showErrors(fields, errors)
    if (Object.keys(errors).length) return
    const payload = editing ? changedPersonFields(values, previous) : personPayload(values)
    if (!Object.keys(payload).length) { feedback.replaceChildren(message('No hay cambios para guardar.', 'info')); return }
    const summary = el('div', {}, el('p', {}, editing
      ? 'Se guardarán únicamente los campos modificados. Identificador e historial se conservan.'
      : 'Se registrarán estos datos administrativos, sin captura facial.'),
    dataGrid(Object.entries(payload).map(([key, value]) => [PERSON_FIELDS[key].label,
      value === null ? editing ? 'Se retirará este dato opcional' : 'No registrado' : value])))
    void flow.run(editing ? 'Confirmar edición de Persona' : 'Confirmar registro de Persona',
      summary,
      () => editing ? api.updatePerson(params.id, payload) : api.createPerson(payload),
      (saved) => { baseline = JSON.stringify(read()); navigate('/personas/' + saved.id_persona, { replace: true }) }, save,
      { confirmLabel: editing ? 'Confirmar edición' : 'Confirmar registro' })
  })
  void start()
  return () => { active = false; flow.destroy(); controller.abort(); view.remove() }
}
