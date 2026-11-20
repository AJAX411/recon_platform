/** SVG inline locales y decorativos; el botón o enlace contenedor aporta el nombre accesible. */
export function icon(kind) {
  const ns = 'http://www.w3.org/2000/svg'
  const svg = document.createElementNS(ns, 'svg')
  for (const [key, value] of Object.entries({ 'aria-hidden': 'true', width: 22, height: 22,
    viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.8' })) svg.setAttribute(key, value)
  const path = document.createElementNS(ns, 'path')
  path.setAttribute('d', kind.startsWith('eye')
    ? 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z'
    : 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4M12 2V1')
  svg.append(path)
  if (kind.startsWith('eye')) {
    const circle = document.createElementNS(ns, 'circle')
    circle.setAttribute('cx', '12'); circle.setAttribute('cy', '12'); circle.setAttribute('r', '3')
    svg.append(circle)
    if (kind === 'eye-off') {
      const slash = document.createElementNS(ns, 'path')
      slash.setAttribute('d', 'M3 3 21 21')
      svg.append(slash)
    }
  }
  return svg
}
