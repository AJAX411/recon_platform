/** Reglas de los ocho campos administrativos y payload parcial; no incorpora cuentas, fotos ni enrolamiento. */
// Solo los ocho campos administrativos del contrato vigente P0.
export const PERSON_FIELDS = {
  primer_nombre: { label: 'Primer nombre', max: 100, required: true },
  segundo_nombre: { label: 'Segundo nombre', max: 100 },
  primer_apellido: { label: 'Primer apellido', max: 100, required: true },
  segundo_apellido: { label: 'Segundo apellido', max: 100 },
  tipo_persona: { label: 'Tipo de Persona', max: 50, required: true },
  tipo_documento: { label: 'Tipo de documento', max: 20, required: true },
  numero_documento: { label: 'Número de documento', max: 30, required: true },
  identificador_institucional: { label: 'Identificador institucional', max: 50 },
}

export function initialPersonValues(person = {}) {
  return Object.fromEntries(Object.keys(PERSON_FIELDS).map((key) => [key, person?.[key] ?? '']))
}

export function personPayload(values) {
  return Object.fromEntries(Object.entries(PERSON_FIELDS).map(([key, field]) => {
    const value = values[key].trim()
    return [key, value || (field.required ? '' : null)]
  }))
}

export function validatePerson(values, types, { previous, documentTypes = [], catalogReady = false } = {}) {
  const errors = {}
  for (const [key, field] of Object.entries(PERSON_FIELDS)) {
    const value = values[key].trim()
    if (field.required && !value) errors[key] = 'Este campo es obligatorio.'
    else if (value.length > field.max) errors[key] = `Usa como máximo ${field.max} caracteres.`
  }
  if (values.tipo_persona && !types.some((type) => type.nombre === values.tipo_persona && type.estado === 'ACTIVO')) {
    errors.tipo_persona = 'Selecciona un Tipo de Persona disponible.'
  }
  if (values.tipo_persona === 'ESTUDIANTE' && !values.identificador_institucional.trim()) {
    errors.identificador_institucional = 'Obligatorio para ESTUDIANTE.'
  }
  const current = personPayload(values)
  const original = previous ? personPayload(initialPersonValues(previous)) : null
  const documentChanged = !original || current.tipo_documento !== original.tipo_documento
    || current.numero_documento !== original.numero_documento
  if (documentChanged && !errors.tipo_documento) {
    if (!catalogReady) errors.tipo_documento = 'El catálogo no está disponible para asignar un documento. Reintenta su consulta.'
    else if (!documentTypes.some((type) => type.codigo === current.tipo_documento && type.habilitado_para_altas)) {
      errors.tipo_documento = 'Selecciona un tipo habilitado al cambiar el tipo o número de documento.'
    }
  }
  return errors
}

export function changedPersonFields(values, previous) {
  const current = personPayload(values)
  const original = personPayload(initialPersonValues(previous))
  return Object.fromEntries(Object.entries(current).filter(([key, value]) => value !== original[key]))
}
