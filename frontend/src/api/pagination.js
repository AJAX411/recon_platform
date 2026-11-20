/** Construye parámetros de paginación y filtros con URLSearchParams sin concatenar valores sin codificar. */
export function pagePath(base, filters = {}, offset = 0, limit = 20) {
  const params = new URLSearchParams({ limite: String(limit), desplazamiento: String(offset) })
  for (const [key, value] of Object.entries(filters)) {
    if (value !== '' && value !== null && value !== undefined) params.set(key, String(value))
  }
  return `${base}?${params}`
}
