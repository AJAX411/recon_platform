/** Construye etiqueta/control/error asociados y aplica validación accesible; las reglas del negocio se verifican también en backend. */
import { el } from './dom.js'

export function field(id, label, { value = '', options, ...attrs } = {}) {
  const input = options ? el('select', { id, name: id, className: 'form-select', ...attrs })
    : el('input', { id, name: id, className: 'form-control', ...attrs })
  if (options) setOptions(input, options, value)
  else input.value = value ?? ''
  const error = el('div', { id: id + '-error', className: 'invalid-feedback' })
  input.setAttribute('aria-describedby', error.id)
  return { input, error, node: el('div', { className: 'mb-3' },
    el('label', { htmlFor: id, className: 'form-label' }, label), input, error) }
}
export function setOptions(input, options, value = input.value) {
  input.replaceChildren(el('option', { value: '' }, 'Seleccionar'),
    ...options.map((option) => el('option', { value: option.value, disabled: option.disabled }, option.label)))
  input.value = value ?? ''
}
export function showErrors(fields, errors) {
  for (const [name, f] of Object.entries(fields)) {
    f.error.textContent = errors[name] || ''
    f.input.classList.toggle('is-invalid', Boolean(errors[name]))
    f.input.setAttribute('aria-invalid', String(Boolean(errors[name])))
  }
  fields[Object.keys(errors)[0]]?.input.focus()
}
