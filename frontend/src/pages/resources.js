/** Metadatos de listados y fichas: rutas, IDs, columnas y representación de nombres; no define entidades nuevas. */
export const personName = (person) => [person.primer_nombre, person.segundo_nombre,
  person.primer_apellido, person.segundo_apellido].filter(Boolean).join(' ')
const state = { key: 'estado', label: 'Estado', options: ['ACTIVO', 'INACTIVO'] }
export const resources = {
  people: {
    title: 'Personas', root: '/personas', collection: 'personas', list: 'listPeople', get: 'person', id: 'id_persona',
    filters: [{ key: 'tipo_documento', label: 'Tipo de documento exacto (incluye histórico)', max: 20 },
      { key: 'numero_documento', label: 'Número de documento', max: 30 },
      { key: 'identificador_institucional', label: 'Identificador institucional' },
      { key: 'tipo_persona', label: 'Tipo de Persona', options: [] }, state],
    columns: ['Nombre', 'Tipo de documento', 'Número de documento', 'Tipo de Persona', 'Estado', 'Detalle'],
    cells: (p) => [personName(p), p.tipo_documento, p.numero_documento, p.tipo_persona, p.estado],
    fields: [['Primer nombre', 'primer_nombre'], ['Segundo nombre', 'segundo_nombre'],
      ['Primer apellido', 'primer_apellido'], ['Segundo apellido', 'segundo_apellido'],
      ['Tipo de documento', 'tipo_documento'], ['Número de documento', 'numero_documento'],
      ['Tipo de Persona', 'tipo_persona'], ['Identificador institucional', 'identificador_institucional'], ['Estado', 'estado']],
    newPath: '/personas/nueva', newLabel: 'Registrar Persona',
  },
  users: {
    title: 'Usuarios de plataforma', root: '/usuarios', collection: 'usuarios', list: 'listUsers', get: 'user', id: 'id_usuario',
    filters: [], columns: ['Usuario', 'Rol', 'Estado', 'Detalle'], cells: (p) => [p.login, p.rol, p.estado],
    fields: [['Usuario', 'login'], ['Rol', 'rol'], ['Estado', 'estado']],
    newPath: '/usuarios/nuevo', newLabel: 'Crear cuenta',
  },
  points: {
    title: 'Puntos de Acceso', root: '/puntos-acceso', collection: 'puntos', list: 'listPoints', get: 'point', id: 'id_punto_acceso',
    filters: [{ key: 'codigo', label: 'Código exacto', max: 20 }, state],
    columns: ['Código', 'Nombre', 'Estado', 'Detalle'], cells: (p) => [p.codigo, p.nombre, p.estado],
    fields: [['Código', 'codigo'], ['Nombre', 'nombre'], ['Descripción', 'descripcion'], ['Estado', 'estado'],
      ['Fecha de creación (UTC)', 'fecha_creacion'], ['Última actualización (UTC)', 'fecha_actualizacion']],
    newPath: '/puntos-acceso/nuevo', newLabel: 'Crear Punto',
  },
  devices: {
    title: 'Dispositivos Edge', root: '/dispositivos-edge', collection: 'dispositivos', list: 'listDevices', get: 'device', id: 'id_dispositivo',
    filters: [{ key: 'codigo', label: 'Código exacto', max: 20 }, state,
      { key: 'modo_operacion', label: 'Modo de operación', options: ['ENTRADA', 'SALIDA', 'AUTOMATICO'] },
      { key: 'id_punto_acceso', label: 'ID del Punto de Acceso', max: 10 }],
    columns: ['Código', 'Nombre', 'Modo', 'Estado', 'Detalle'], cells: (p) => [p.codigo, p.nombre, p.modo_operacion, p.estado],
    fields: [['Código', 'codigo'], ['Nombre', 'nombre'], ['Punto de Acceso (ID)', 'id_punto_acceso'],
      ['Modo de operación', 'modo_operacion'], ['Estado administrativo', 'estado'],
      ['Última comunicación registrada (UTC)', 'ultima_comunicacion'],
      ['Fecha de creación (UTC)', 'fecha_creacion'], ['Última actualización (UTC)', 'fecha_actualizacion']],
    newPath: '/dispositivos-edge/nuevo', newLabel: 'Registrar dispositivo',
  },
}
