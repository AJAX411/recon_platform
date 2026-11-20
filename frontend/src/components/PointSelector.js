import { button, el, loading, message } from './dom.js'
import { field, setOptions } from './Fields.js'

export function mountPointSelector({ api, activeOnly = false, onChange = () => {}, label = 'Punto de Acceso', showCodeFilter = true }) {
  const code = field('codigo_punto', 'Código exacto (opcional)', { maxLength: 20 })
  const select = field('id_punto_acceso', label, { options: [] })
  const summary = el('p', { role: 'status' })
  const status = el('div')
  const counter = el('span')
  let selected = null, offset = 0, appliedCode = '', controller = null, active = true, rows = []
  const previous = button('Página anterior de Puntos', () => { offset = Math.max(0, offset - 20); void load() })
  const next = button('Página siguiente de Puntos', () => { offset += 20; void load() })
  function draw() {
    const choices = selected && !rows.some((p) => p.id_punto_acceso === selected.id_punto_acceso) ? [selected, ...rows] : rows
    setOptions(select.input, choices.map((p) => ({ value: p.id_punto_acceso, label: p.nombre + ' · ' + p.codigo })), selected?.id_punto_acceso)
    summary.textContent = selected ? 'Seleccionado: ' + selected.nombre + ' · ' + selected.codigo : 'Selecciona un Punto explícitamente.'
  }
  select.input.addEventListener('change', () => {
    selected = [...rows, ...(selected ? [selected] : [])].find((p) => p.id_punto_acceso === Number(select.input.value)) || null
    draw(); onChange(selected)
  })
  function search() { appliedCode = code.input.value.trim(); offset = 0; selected = null; onChange(null); void load() }
  code.input.addEventListener('input', () => {
    selected = null; onChange(null); draw(); select.input.disabled = code.input.value.trim() !== appliedCode
  })
  code.input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { event.preventDefault(); search() }
  })
  const node = el('fieldset', { className: 'point-selector' }, el('legend', {}, label),
    ...(showCodeFilter ? [code.node, button('Buscar Punto', search)] : []), select.node, summary, status,
    el('div', { className: 'form-actions' }, previous, counter, next))
  async function load() {
    controller?.abort(); controller = new AbortController()
    const signal = controller.signal
    select.input.disabled = true; previous.disabled = true; next.disabled = true
    status.replaceChildren(loading())
    try {
      const data = await api.listPoints({ ...(activeOnly ? { estado: 'ACTIVO' } : {}), codigo: appliedCode }, offset, signal)
      if (!active || signal.aborted) return
      if (!Array.isArray(data?.puntos)) throw new Error('No se recibió una página válida de Puntos.')
      rows = activeOnly ? data.puntos.filter((p) => p.estado === 'ACTIVO') : data.puntos
      rows = rows.filter((p) => Number.isSafeInteger(p.id_punto_acceso) && p.id_punto_acceso > 0)
      draw()
      status.replaceChildren(...(rows.length ? [] : [message('No hay Puntos en esta página.', 'info')]))
      counter.textContent = 'Página de Puntos ' + (offset / 20 + 1)
      previous.disabled = offset === 0
      next.disabled = data.puntos.length < 20 || offset + 20 > 1_000_000
      select.input.disabled = code.input.value.trim() !== appliedCode
    } catch (error) {
      if (!active || signal.aborted) return
      draw()
      status.replaceChildren(message(error.message), button('Reintentar Puntos', load))
      previous.disabled = offset === 0
      select.input.disabled = !selected
    }
  }
  void load()
  return { node, select: select.input, getSelected: () => selected,
    clear: () => { selected = null; draw(); onChange(null) },
    reload: load,
    reset: () => { code.input.value = ''; appliedCode = ''; offset = 0; selected = null; onChange(null); void load() },
    destroy: () => { active = false; controller?.abort(); node.remove() } }
}
