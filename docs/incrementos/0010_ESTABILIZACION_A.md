# Incremento 0010 — Macroencargo A

Alcance autorizado: UX Vanilla, organización backend por dominios y documentación
controlada. No autoriza Macro B/G6 real, Docker, Azure, MySQL, migraciones,
instalación, red externa ni Git de escritura. Incremento **ABIERTO**.

## Verificado como existente y conservado

Vanilla ya era operativa en raíz. Se conservaron router/estado/cliente HTTP,
ojos de detalle con nombres accesibles, movimientos modales desde Inicio,
incidencias directas desde Alertas, eliminación de botones de actualización
permanentes, ausencia de selector facial, acciones de estado/edición aprobadas,
formulario manual único vertical, catálogo de seis documentos y minimización O.
El backend ya tenía la estructura directa aprobada por capacidades.

## Cambios puntuales

- Menú: Perfil de solo lectura y cierre al abandonar sus controles por teclado.
- Personas: resumen de los campos enviados; Confirmar registro/Confirmar edición
  y Cancelar, usando el modal y el control de envío únicos que ya existían.
- Alta Edge: se retira de esa pantalla el filtro por código exacto; se conserva
  el selector existente, carga asíncrona, paginación y selección explícita.
- Resumen: revalidación por actividad tras 30 s, sin polling ni solicitudes
  concurrentes duplicadas. Se eliminan los listeners al desmontar.
- Personas: acción Eliminar deshabilitada con explicación visible; no existe
  mutación de anonimización, DELETE ni una política inventada. Desactivar sigue
  siendo la operación reversible de estado, con datos/historial conservados.
- Índice y guías actuales; legado, candidata, cachés y documentos anteriores
  conservados. No se mueven ni borran archivos históricos.

## Propuesta acotada para eliminación de datos — no implementada

La solicitud docente de anonimizar requiere definir qué campos pueden retirarse,
retención y base institucional, reversibilidad, unicidad documental tras supresión,
permisos y auditoría mínima, y proyecciones del historial. Debe conservarse
`id_persona` y la integridad de sus referencias, separando Persona de cuenta web.

Propuesta de contrato funcional para revisión: una operación distinta de cambiar
estado, actor autenticado y autorizado, Persona existente identificada por su ID,
transacción única y auditoría sin valores personales retirados. Campos,
precondiciones, códigos HTTP y eventual endpoint siguen **PENDIENTES** hasta
política aprobada. No se añade ruta o payload a OpenAPI ni se habilita el botón.
La UI distingue expresamente esa carencia de Desactivar; no simula cumplimiento.

## Puertas pendientes

189/189 Vitest, ESLint/build y comprobaciones backend aisladas satisfactorios.
Los resultados no sustituyen G6 con MySQL/browser. C15/D08/D09/D13 siguen abiertos;
D12 requiere constatación humana y no queda aprobado por DOM. Revisar Macro A
antes de autorizar Macro B. No retirar React ni candidata para forzar una
etiqueta de limpieza o release.
