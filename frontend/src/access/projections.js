/** Comprueba las claves permitidas de OPERADOR y muestra hora aproximada; no promete anonimato absoluto. */
import { formatBogota } from './format.js'

export const reducedFields = ['tipo_movimiento', 'resultado', 'hora_local_aproximada']
export function checkReduced(rows) {
  if (!Array.isArray(rows) || rows.some((row) => !row || Object.keys(row).some((key) => !reducedFields.includes(key)))) {
    throw new Error('La proyección reducida contiene datos no permitidos.')
  }
  return rows
}
export function approximateTime(value) {
  if (!value || !Number.isFinite(new Date(value).getTime())) return 'Hora no disponible'
  const time = new Date(value)
  // Defensa adicional de presentación; el contrato ya entrega precisión de hora.
  time.setUTCMinutes(0, 0, 0)
  return formatBogota(time.toISOString())
}
