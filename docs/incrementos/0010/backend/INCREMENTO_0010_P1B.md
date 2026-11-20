# Incremento 0010 — P1-B: catálogo documental y V2

> Continuidad 18/11/2026: [ADR-D0-BE-01](../../../../backend/ADR_D0_BE_01_ORGANIZACION_CAPACIDADES.md)
> refina ubicaciones internas; los enlaces de código apuntan al destino vigente.
> Los resultados y estados de este incremento conservan su fecha histórica.

**Estado:** candidato local para revisión independiente, 17/11/2026. No publicado,
sin cierre del Incremento 0010. Se conserva P0/P1-A y sus aprobaciones técnicas
con reservas. El encargo expreso del responsable ratifica V2 y seis códigos.

## Catálogo y compatibilidad

[Fuente inmutable](../../../../backend/src/recon_platform/personas/tipos_documento.py):
CC — Cédula de ciudadanía; TI — Tarjeta de identidad; CE — Cédula de extranjería;
PA — Pasaporte; PPT — Permiso por Protección Temporal; RC — Registro civil de
nacimiento, en ese orden, todos habilitados. Son códigos internos del proyecto;
no nuevas reglas de edad, ciudadanía, TipoPersona o acceso.

Nuevo GET `/api/v1/personas/tipos-documento`, solo SUPERADMIN/ADMINISTRADOR,
sin parámetros, no-store; 200 `tipos_documento` con `codigo`, `nombre` y
`habilitado_para_altas`. 400 query extra; 401/403 guard vigente; 503 fallo.
La habilitación también se aplica a nuevas asignaciones documentales en edición.
GET `/personas/tipos` conserva su catálogo distinto de TipoPersona.

[Casos de uso](../../../../backend/src/recon_platform/personas/servicio.py): ambas altas
exigen código habilitado. PATCH compara el par normalizado tipo/número con el
anterior; si cambia cualquiera, exige tipo resultante habilitado. Si no cambia,
conserva legado. Lecturas, filtros, respuestas y constructor universal no cierran
el legado. Se mantiene trim exterior, sin uppercase/equivalencias/formato nuevo.

La compatibilidad de entrada se estrecha deliberadamente: antes podían
registrarse códigos libres nuevos; ahora se rechazan con 400. No cambian campos
de Persona, permisos, 201/Location, CSRF, integridad, auditoría o transacción.
El [OpenAPI](../../../../backend/openapi.json) contiene 35 operaciones, una nueva respecto a P0+A.
La regla OBS-P1A-01 sigue vigente: TipoPersona ACTIVO al actualizar incluso omitido.

## React y V2

Formulario común con select nativo consultado por cliente central, sin enum
duplicado en producción. Preserva documento histórico, borradores, cancelación,
foco, confirmación y protección de incertidumbre. Catálogo caído/sin habilitados
bloquea altas y cambio documental; permite otros cambios con par idéntico y demás
reglas satisfechas. Listado/detalle muestran etiqueta disponible o código literal,
sin modificar DTO ni cerrar el filtro histórico.

V2 moderniza composición de login, cabecera clara/navegación navy, dashboard,
tablas/formularios/detalles y estados compartidos. Misma identidad Campus claro,
stack y rutas. Guards, providers, claves de aislamiento y envío del login se
conservan; no polling. Incidencias de cabecera reales, sin falsa bandeja.
Cuatro métricas S/A, cobertura/frescura y hora aproximada O se mantienen.

## Pruebas y límites

[Tests catálogo/backend](../../../../backend/tests/unit/test_catalogo_documental_0010.py) y tests
frontend cubren reglas/HTTP/DOM con dobles y SQLite exclusivamente en memoria.
Los resultados ejecutados, barreras y hashes se entregan en el paquete externo;
no confundirlos con MySQL, navegador autenticado o medición en píxeles.

- Filas reales pobladas OPERADOR: NO EVALUADAS.
- Zoom real 200 %: NO EJECUTADO; sin conformidad integral de accesibilidad.
- Flujos nuevos P1-A en web/base real: NO EJECUTADOS.

Correo APLAZADO, sin campos/validadores/migraciones de contacto. No modelos
físicos, dependencias o migraciones nuevas; sin MySQL, servicios reales,
instalaciones o Git de escritura durante este encargo. IAM delegado P1-C,
fotografía y enrolamiento/Edge fuera; ACTIVO no acredita enrolamiento ni acceso.
No se modificaron AGENTS ni Contexto Maestro v1.7. Se detiene para revisión.
