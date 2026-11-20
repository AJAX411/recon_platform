/** Filtros y paginación reutilizables; el formulario entrega valores a la vista sin ejecutar SQL o mutar el negocio. */
import { button, el, message } from './dom.js'

export function filters(specs, values, onApply, onClear) {
  const form = el('form', { className: 'filter-panel', 'aria-label': 'Filtros de consulta' })
  const invalid = el('div')
  const controls = new Map()
  const fields = el('div', { className: 'filter-grid' })
  for (const spec of specs) {
    const id = 'filtro-' + spec.key
    const input = spec.options
      ? el('select', { id, name: spec.key, className: 'form-select' }, el('option', { value: '' }, 'Todos'),
        spec.options.map((value) => el('option', { value }, value)))
      : el('input', { id, name: spec.key, type: spec.type || 'text', maxLength: spec.max || 50, className: 'form-control' })
    input.value = values[spec.key] || ''
    controls.set(spec.key, input)
    fields.append(el('div', {}, el('label', { htmlFor: id, className: 'form-label' }, spec.label), input))
  }
  form.addEventListener('submit', (event) => {
    event.preventDefault()
    const draft = Object.fromEntries([...controls].map(([key, input]) => [key, input.value.trim()]))
    const failure = onApply(draft)
    invalid.replaceChildren(...(failure ? [message(failure)] : []))
  })
  form.append(invalid, fields, el('div', { className: 'filter-actions' },
    el('button', { className: 'btn btn-primary', type: 'submit' }, 'Aplicar filtros'),
    button('Limpiar', () => { for (const input of controls.values()) input.value = ''; invalid.replaceChildren(); onClear() })))
  const details = el('details', { className: 'filter-disclosure' },
    el('summary', { className: 'filter-toggle' }, 'Filtros de consulta'), form)
  if (Object.values(values).some(Boolean)) details.open = true
  return { node: details, controls }
}
export function pagination(offset, count, change) {
  return el('nav', { className: 'pagination-controls', 'aria-label': 'Paginación de resultados' },
    el('span', { className: 'muted' }, 'Página ' + (Math.floor(offset / 20) + 1)),
    button('Anterior', () => change(Math.max(0, offset - 20)), { disabled: offset === 0 }),
    button('Siguiente', () => change(offset + 20), { disabled: count < 20 || offset + 20 > 1_000_000 }))
}
