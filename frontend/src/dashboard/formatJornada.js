export function formatJornada(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return 'No disponible'
  const day = new Date(`${value}T12:00:00-05:00`)
  if (Number.isNaN(day.getTime())) return 'No disponible'
  return new Intl.DateTimeFormat('es-CO', {
    timeZone: 'America/Bogota', day: 'numeric', month: 'long', year: 'numeric',
  }).format(day)
}
