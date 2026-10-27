# Manifiesto de cierre documental · Incremento 0008

**Proyecto:** Recon Facial — frontend de Eventos de Acceso manuales.

**Corte:** 27/10/2026.

**Estado:** **CIERRE TÉCNICO PROPUESTO — PENDIENTE DE REVISIÓN INDEPENDIENTE FINAL Y AUTORIZACIÓN DE PUBLICACIÓN.**

**Baseline de gobierno:** Contexto Maestro v1.7 OFICIAL (25/10/2026). Las reglas de EventoAcceso del incremento 0006 mantienen su alcance PROVISIONAL aprobado; este cierre no las eleva a CONFIRMADO.

## Fuentes y criterio de evidencia

- Se consultaron el Contexto Maestro v1.7 OFICIAL, la resolución arquitectónica formal 0006 y la especificación funcional 0006 v1.0. Para el estado del repositorio se revisaron [AGENTS.md](../AGENTS.md), el [manifiesto de definición e implementación 0008](./INCREMENTO_0008_BLOQUE1_PROPUESTA.md), los manifiestos históricos [0007-A](./INCREMENTO_0007-A.md) y [0007-B](./INCREMENTO_0007-B.md), el [README frontend](./README.md), el [contrato OpenAPI](../backend/openapi.json), las [rutas Flask de Eventos](../backend/src/recon_platform/accesos/eventos_api.py) y la [proyección de persistencia](../backend/src/recon_platform/accesos/eventos_infraestructura.py).
- Para describir la entrega se inspeccionaron las [rutas React](./src/App.jsx), el [registro manual](./src/pages/AccessManualPage.jsx), [historial](./src/pages/AccessHistoryPage.jsx), [alertas](./src/pages/AccessAlertsPage.jsx), [detalle de incidencia](./src/pages/AccessIncidentPage.jsx), el [cliente HTTP](./src/api/http.js), el [servicio de Eventos](./src/api/eventos.js), las [reglas de presentación](./src/styles.css) y las pruebas [de interfaz](./src/test/access.test.jsx) y [de contrato HTTP](./src/test/access-api.test.js).
- **Evidencia comunicada por el responsable:** aprobación de Bloque 1, revisión independiente favorable del Bloque 2 y de la corrección de foco, resultados automatizados y validación real del 27/10/2026 descritos abajo. Codex no abrió el ZIP de revisión, no consultó MySQL ni el respaldo y no ejecutó de nuevo las pruebas en esta tarea documental. La inspección actual de archivos y Git es evidencia distinta de esos resultados históricos.

## Alcance entregado

El frontend 0008 agrega cuatro rutas humanas bajo la sesión y CSRF existentes: registro de ENTRADA/SALIDA manual, historial por rol, alertas consultables y detalle administrativo de incidencia. OPERADOR utiliza la búsqueda específica de Personas elegibles, consulta historial reducido de jornada y conteos de alertas; ADMINISTRADOR y SUPERADMIN tienen historial/alertas ampliados, filtros y detalle. Flask sigue decidiendo permisos, estados, actor, instante, método, resultado e incidencia. La jornada funcional se calcula en `America/Bogota`. La hora aproximada del historial de OPERADOR es la **proyección reducida aprobada**: el backend la redondea al inicio de la hora; no es un error de fecha ni una afirmación de presencia real.

El cliente envía exactamente los tres campos de la declaración manual con una clave UUIDv4. La misma clave y el mismo cuerpo se conservan en memoria para un reintento explícito de resultado incierto, con barrera síncrona contra doble envío. La corrección posterior de foco mantiene el panel de estado enfocado desde el envío hasta éxito o error, sin modificar el componente compartido de confirmación. No hay reconocimiento facial, enrolamiento, observaciones biométricas operativas, conexión Raspberry, apertura física, push ni WebSocket en este incremento.

## Resultados del Bloque 3 comunicados por el responsable

| Evidencia | Resultado comunicado | Alcance y límite |
|---|---|---|
| Revisión independiente | Bloque 1 aprobado; implementación del Bloque 2 y corrección de foco aprobadas. | La revisión final de este cierre documental sigue pendiente. |
| Pruebas automatizadas | **82/82** aprobadas con ejecución secuencial y timeout de 10 segundos; build y ESLint satisfactorios según evidencia anterior. | Con la configuración predeterminada se observaron timeouts intermitentes, incluso en pruebas ajenas a 0008. Estos resultados no se reejecutaron en esta tarea. |
| Entorno real del 27/10/2026 | React + Flask + MySQL `recon_dev` con revisión `0006_evento_acceso`, según el responsable. | No se volvió a consultar la identidad ni la revisión del esquema en este cierre documental. No equivale a validación de producción. |
| Tres declaraciones manuales | Tres respuestas HTTP `201`: SALIDA con `SALIDA_SIN_ENTRADA_DEL_DIA`, ENTRADA sin incidencia y SALIDA sin incidencia. | Confirman tres altas distintas bajo la secuencia observada; no prueban reenvío idempotente. No se documentan identificadores ni datos personales. |
| Consultas y permisos | Historial reducido de OPERADOR y ampliado de SUPERADMIN; alertas, detalle administrativo de incidencia y filtros de historial comprobados. | Se refiere a los flujos informados, sin certificar toda la matriz de permisos ni accesibilidad general. |
| Postflight MySQL | Tres EventosAcceso, tres claves de idempotencia distintas y no nulas, y tres registros exitosos de auditoría manual. | La distinción de claves acredita declaraciones diferentes, **no** un replay. Los tests automatizados cubren el reintento con la misma clave; no hay evidencia de un `200` de replay en la validación real. |
| Estado administrativo posterior | Cuenta OPERADOR de prueba y Punto ficticio devueltos a INACTIVO. | No se infieren otros cambios ni se realizaron escrituras desde Codex en esta tarea. |
| Respaldo | Respaldo privado posterior a 0008 creado y verificado con SHA-256. | Se hizo **después** de las tres escrituras: no acredita una copia previa a esa validación. La restauración no se ensayó y el hash por sí solo no prueba recuperabilidad. No se adjunta el respaldo ni su contenido. |

## Comprobaciones actuales y estado Git

Al iniciar esta tarea, `git status --short --branch --untracked-files=all` mostró `main`, HEAD `c38a09f7f2c8a4fa7c68e603ad46081131aa6b25`, **seis archivos modificados y dieciséis nuevos sin seguimiento** del trabajo previo de 0008, sin staging ni commit. `git diff --stat` cubría solo los archivos ya seguidos. Se comprobó que este archivo de cierre **no existía** antes de crearlo. La inspección actual fue de lectura de código, contrato, pruebas y documentos; no incluyó ejecución de tests, servidor, migración, MySQL ni prueba funcional de escritura.

Este cierre añade únicamente el archivo presente; los otros cambios pendientes permanecen intactos. Su inclusión en Git, revisión final, commit y publicación continúan bajo control exclusivo del responsable.

## Accesibilidad, riesgos residuales y pendientes

**Zoom al 200 % — riesgo residual y validación pendiente aceptada.** El responsable decidió aplazar expresamente esta comprobación para un futuro incremento dedicado a UX/UI, diseño adaptable y accesibilidad. La inspección estática muestra tablas dentro de un contenedor `table-responsive` y navegación lateral con desplazamiento propio bajo 900 px; los formularios y rejillas pasan a menos columnas en los cortes de 900/650 px. También muestra `body { min-width: 320px; }`: si el viewport efectivo tras zoom baja de 320 píxeles CSS, habrá desbordamiento horizontal del documento. No se midió el comportamiento al 200 % en el viewport objetivo; por ello no se declara conformidad de accesibilidad ni un defecto bloqueante demostrado. El incremento futuro deberá comparar `document.documentElement.scrollWidth` con `clientWidth`, identificar cualquier elemento que desborde, distinguir el scroll interno del global y comprobar lectura, teclado, foco y acceso a los controles. Esta validación diferida queda registrada como salvedad aceptada del cierre técnico 0008.

**Privacidad operativa.** El GET vigente de Personas elegibles envía el criterio de búsqueda en la query; permanece pendiente verificar que los logs HTTP no conserven nombre, documento o identificador institucional antes de operar con datos personales reales. La interfaz no guarda la declaración ni la clave en almacenamiento persistente. Tras una recarga con resultado incierto no hay recuperación automática: se indica revisión con un administrador. La política general de retención y otros aspectos biométricos siguen PENDIENTES según v1.7.

**Mejoras posteriores no bloqueantes por la evidencia disponible:** pulir textos UX, espacios y la navegación de regreso desde detalle de incidencia. Actualmente el enlace de regreso del detalle lleva a alertas aunque la consulta pudiera originarse en historial; no altera permisos ni el evento. Estas mejoras requieren un alcance posterior y no se ejecutan en este cierre.

## Conclusión propuesta

La evidencia histórica comunicada respalda el incremento web manual dentro de su alcance aprobado. Se **propone el cierre técnico de 0008 con la verificación de zoom al 200 % expresamente aplazada y aceptada como riesgo residual**, sujeto únicamente a la revisión independiente final de este archivo y a la autorización de publicación del responsable. No se declara conformidad de accesibilidad ni un defecto bloqueante demostrado. El cierre tampoco certifica producción, restaurabilidad del respaldo, idempotencia real por replay ni integración biométrica/Edge. No se realizó commit ni push.
