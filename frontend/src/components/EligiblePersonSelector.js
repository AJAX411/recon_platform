import { button, el, loading, message } from './dom.js'
import { field, setOptions } from './Fields.js'

export function mountEligiblePersonSelector({ api, onChange = () => {} }) {
  const criterion = field('persona_criterio', 'Buscar Persona por', { value: 'nombre', options: [
    { value: 'nombre', label: 'Primer nombre o apellido' }, { value: 'documento', label: 'Número de documento exacto' },
    { value: 'institucional', label: 'Identificador institucional exacto' },
  ] })
  const value = field('persona_valor', 'Valor de búsqueda de Persona', { maxLength: 50 })
  const selected = field('persona_elegida', 'Seleccionar Persona', { options: [] })
  const status = el('div')
  let active = true, controller = null, rows = [], person = null
  const node = el('fieldset', {}, el('legend', {}, '1. Seleccionar Persona ACTIVA'), criterion.node, value.node,
    button('Buscar Persona', search), selected.node, status)
  function clear() {
    controller?.abort(); rows = []; person = null; setOptions(selected.input, []); status.replaceChildren(); onChange(null)
  }
  value.input.addEventListener('input', clear)
  criterion.input.addEventListener('change', clear)
  value.input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { event.preventDefault(); void search() }
  })
  selected.input.addEventListener('change', () => {
    person = rows.find((p) => p.id_persona === Number(selected.input.value)) || null
    onChange(person)
  })
  async function search() {
    clear()
    const text = value.input.value.trim()
    if (text.length < 3 || text.length > 50 || [...text].some((c) => c.charCodeAt(0) < 32)
      || !['nombre', 'documento', 'institucional'].includes(criterion.input.value)) {
      status.replaceChildren(message('Escribe entre 3 y 50 caracteres válidos.')); value.input.focus(); return
    }
    controller = new AbortController()
    const signal = controller.signal
    status.replaceChildren(loading())
    try {
      const data = await api.eligiblePeople(criterion.input.value, text, signal)
      if (!active || signal.aborted) return
      if (!Array.isArray(data?.personas) || data.personas.some((p) =>
        !Number.isSafeInteger(p.id_persona) || p.id_persona <= 0 || typeof p.nombre !== 'string')) {
        throw new Error('No se recibieron Personas elegibles válidas.')
      }
      rows = data.personas
      setOptions(selected.input, rows.map((p) => ({
        value: p.id_persona, label: p.nombre + ' · ' + p.tipo_documento + ' terminado en ' + p.documento_final,
      })))
      status.replaceChildren(...(rows.length ? rows.length === 20
        ? [message('Se muestran hasta veinte coincidencias. Refina la búsqueda si es necesario.', 'info')] : []
        : [message('No hay Personas activas con esta búsqueda.', 'info')]))
    } catch (error) {
      if (active && !signal.aborted) status.replaceChildren(message(error.message))
    }
  }
  return { node, getSelected: () => person, clear,
    reset: () => { criterion.input.value = 'nombre'; value.input.value = ''; clear() },
    destroy: () => { active = false; controller?.abort(); node.remove() } }
}
