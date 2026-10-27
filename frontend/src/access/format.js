export const INCIDENCE_LABELS = {
  ENTRADA_REPETIDA: 'Entrada repetida',
  SALIDA_REPETIDA: 'Salida repetida',
  SALIDA_SIN_ENTRADA_DEL_DIA: 'Salida sin entrada de la jornada',
}

export const ADMIN_FILTERS = {
  id_persona: '', id_punto_acceso: '', tipo_movimiento: '', resultado: '',
  tipo_incidencia_secuencia: '', desde: '', hasta: '',
}

const dayFormatter = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/Bogota', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
})

function bogotaWallTime(instant) {
  const parts = Object.fromEntries(dayFormatter.formatToParts(new Date(instant))
    .filter((part) => part.type !== 'literal').map((part) => [part.type, Number(part.value)]))
  return Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute, parts.second)
}

// Convert a civil midnight in Bogotá to an instant without using the browser time zone.
export function bogotaDayStart(dateText) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateText)) throw new Error('Fecha inválida.')
  const target = Date.parse(`${dateText}T00:00:00Z`)
  if (!Number.isFinite(target) || new Date(target).toISOString().slice(0, 10) !== dateText) {
    throw new Error('Fecha inválida.')
  }
  let instant = target + 5 * 60 * 60 * 1000
  for (let attempt = 0; attempt < 3; attempt += 1) instant += target - bogotaWallTime(instant)
  if (bogotaWallTime(instant) !== target) throw new Error('No se pudo convertir la fecha de Bogotá.')
  return new Date(instant).toISOString()
}

export function nextBogotaDayStart(dateText) {
  bogotaDayStart(dateText)
  const next = new Date(Date.parse(`${dateText}T00:00:00Z`) + 24 * 60 * 60 * 1000)
    .toISOString().slice(0, 10)
  return bogotaDayStart(next)
}

export function validateAdminFilters(filters) {
  for (const name of ['id_persona', 'id_punto_acceso']) {
    const value = String(filters[name] || '').trim()
    if (value && (!/^[1-9]\d*$/.test(value) || value.length > 10)) {
      return 'Los identificadores deben ser enteros positivos de hasta 10 dígitos.'
    }
  }
  try {
    if (filters.desde) bogotaDayStart(filters.desde)
    if (filters.hasta) nextBogotaDayStart(filters.hasta)
  } catch {
    return 'Selecciona fechas válidas para Bogotá.'
  }
  if (filters.desde && filters.hasta && filters.desde > filters.hasta) {
    return 'El día final debe ser igual o posterior al inicial.'
  }
  return ''
}

export function adminFiltersToApi(filters) {
  const { desde, hasta, ...others } = filters
  return {
    ...others,
    desde: desde ? bogotaDayStart(desde) : '',
    hasta: hasta ? nextBogotaDayStart(hasta) : '',
  }
}

export function formatBogota(value) {
  if (!value) return 'No registrado'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Fecha no disponible'
  return new Intl.DateTimeFormat('es-CO', {
    timeZone: 'America/Bogota', dateStyle: 'medium', timeStyle: 'short', hour12: false,
  }).format(date)
}
