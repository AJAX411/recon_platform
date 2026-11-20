export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag)
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue
    if (key === 'className') node.className = value
    else if (key in node && !key.startsWith('aria-') && key !== 'role') node[key] = value
    else node.setAttribute(key, String(value))
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue
    // El texto del servidor siempre se inserta como texto, nunca como HTML.
    node.append(child instanceof Node ? child : document.createTextNode(String(child)))
  }
  return node
}
export function button(text, onClick, attrs = {}) {
  const node = el('button', { type: 'button', className: 'btn btn-outline-secondary', ...attrs }, text)
  node.addEventListener('click', onClick)
  return node
}
export const link = (href, text, attrs = {}) => el('a', { href, ...attrs }, text)
export const message = (text, tone = 'danger') => el('div', {
  className: 'alert alert-' + tone, role: tone === 'danger' ? 'alert' : 'status',
}, text)
export const loading = () => message('Cargando información…', 'info')
export function page(title, intro = '') {
  return el('section', { className: 'page-section' }, el('div', { className: 'page-head' },
    el('div', {}, el('h1', {}, title), intro && el('p', { className: 'page-intro' }, intro))))
}
export function dataGrid(items) {
  return el('dl', { className: 'detail-grid' }, items.map(([label, value]) =>
    el('div', {}, el('dt', {}, label), el('dd', {}, value === null || value === undefined || value === '' ? 'No registrado' : value))))
}
