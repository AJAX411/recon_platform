/** Tabla semántica y enlaces de detalle accesibles; cada celda corresponde a un campo definido por la vista. */
import { button, el, link } from './dom.js'
import { icon } from './Icons.js'

export function detailAction(label, { href, state, onClick } = {}) {
  const attrs = { className: 'detail-link detail-link-compact', 'aria-label': label, title: label }
  const action = href ? link(href, '', attrs) : button('', onClick, { ...attrs, 'aria-haspopup': 'dialog' })
  if (state) action.navigationState = state
  action.append(icon('eye'))
  return action
}
export function table(caption, columns, rows) {
  const node = el('table', { className: 'table people-table table-with-actions' },
    el('caption', { className: 'visually-hidden' }, caption),
    el('thead', {}, el('tr', {}, columns.map((c) => el('th', { scope: 'col' }, c)))),
    el('tbody', {}, rows.map((row) => el('tr', {}, row.map((value, index) => {
      const cell = el(index === 0 ? 'th' : 'td', index === 0 ? { scope: 'row' } : {})
      if (value instanceof Node) cell.append(value)
      else {
        const text = value === null || value === undefined || value === '' ? 'No registrado' : String(value)
        cell.append(el('span', { className: 'table-value', title: text }, text))
      }
      return cell
    })))))
  return el('div', { className: 'table-responsive', role: 'region', 'aria-label': caption, tabIndex: 0 }, node)
}
