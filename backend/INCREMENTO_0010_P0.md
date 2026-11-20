# Incremento 0010 — P0 controlada

> Continuidad 18/11/2026: [ADR-D0-BE-01](./ADR_D0_BE_01_ORGANIZACION_CAPACIDADES.md)
> refina ubicaciones internas; los enlaces de código apuntan al destino vigente.
> Los resultados y estados de este incremento conservan su fecha histórica.

**Estado:** implementación local para revisión independiente, sin cierre de P0
ni del Incremento 0010. Autorización del responsable: 16/11/2026, encargo Bloque 2
P0 en formatos TXT/MD idénticos (SHA-256
`8339351c094d84b4c976cd4552290704a801ee115427c8e8a89b6b63e54911a0`).
Baseline inicial: `main`, HEAD `8166b006d0a44faadcd2901b851be658ba1be0d3`, limpio.

## Fuentes y decisiones aplicadas

[AGENTS](../AGENTS.md), Contexto Maestro v1.7 OFICIAL (25/10/2026), informes
externos de Bloque 1 y encargo expreso P0. Se verificó lectura del Contexto,
incluida ARQ-BIO-POST16-01, sin modificar su archivo. Documento principal/Anexo 3
no aportados: no se certifica trazabilidad académica completa.

1. Dashboard S/A con conteos reales y ocupación histórica deduplicada; es
   reporting documental, no presencia física certificada ni nueva regla de acceso.
2. IAM A→cualquier O vigente aprobado como dirección para P1; **no implementado**.
   Propuesta acotada ARQ-IAM-0010: A no crea/toca S/A, no cambia roles ni su cuenta;
   S conserva gestión A/O y protección inicial. Antes de P1 formalizar políticas
   de revalidación actor/objetivo y bloqueo ordenado en una transacción, carreras
   con ascensos, consultas filtradas antes de paginar, reset/revocación, entrega
   segura y auditoría de éxitos/fallos sin credenciales. No se inventa propiedad
   por creador; recuperación S y temporalidad/primer cambio requieren definición.
3. Correo nuevo obligatorio con legado compatible y catálogo documental
   explícito: **P1**, sin modelo/migración/endpoint nuevo ahora; códigos pendientes.
4. Registro Persona separado de enrolamiento; P0 solo aviso de capacidad pendiente.
5. Campus claro implementado mediante CSS/Bootstrap; sin dependencias nuevas.

## Arquitectura y contrato aditivo

Nuevo `GET /api/v1/consultas/dashboard`, sin parámetros, con guard/transporte
de sesión humana existentes y `Cache-Control: no-store`. [Controlador](./src/recon_platform/consultas/controlador.py)
→ [servicio](./src/recon_platform/consultas/servicio.py) → puertos
públicos [Accesos](./src/recon_platform/accesos/contratos_consultas.py) y
[Personas](./src/recon_platform/personas/contratos_consultas.py). Composición
construye adaptadores de cada capacidad con la misma sesión. Reporting no
importa repositorios privados de otras capacidades. No tablas/modelos nuevos.

[Unidad de lectura](./src/recon_platform/consultas/unidad_lectura.py)
descarta la lectura implícita del guard, solicita REPEATABLE READ para MySQL y
finaliza con rollback. SQLite usa SERIALIZABLE para pruebas en memoria. La
consistencia real MySQL y su rendimiento se mantienen pendientes de autorización.
El guard de identidad puede actualizar actividad de sesión: GET no significa
ausencia total de escritura en la plataforma en ejecución real.

## Fórmulas y calidad

Un `t` UTC confiable del servidor, compartido en todas las consultas. Jornada
Bogotá `[inicio local, siguiente inicio local)`, convertida a UTC, más `fecha<=t`.

- Entradas/salidas: COUNT de eventos AUTORIZADO del movimiento del día hasta t.
  Incidencia no invalida AUTORIZADO. Replay no crea filas; nueva declaración sí.
- Dentro: último AUTORIZADO por Persona no nula sobre todo el historial disponible,
  orden `(fecha_hora_ocurrencia,id_evento_acceso)`; cuenta una vez si ENTRADA.
  Anti-EXISTS con índices existentes, sin descargar la historia completa.
- RECHAZADO no modifica presencia; Persona/Punto desactivados no borran historia.
- Total Personas: agregado completo, activas e inactivas; sin total de una página.
- Incidencias: COUNT por tipo sobre eventos del día hasta t; suma de grupos disjuntos.
- Últimos movimientos: hasta diez, orden existente; O limitado al día.

Si hay Personas pero ningún historial autorizado, ocupación `null` y
`NO_DISPONIBLE`. Si no hay Personas/eventos, cero comprobado. Historia parcial:
estimación de los sujetos conocidos y cantidad de Personas sin historial
(presencia desconocida). Se informa `HISTORIAL_DISPONIBLE_NO_CERTIFICADO`:
no se conoce/certifica integridad del inicio de observación. Una inconsistencia
de cobertura detectada devuelve ocupación no disponible. No se corrige historia.

## Perfiles, errores y privacidad

[DTO](./src/recon_platform/consultas/dto.py) por allowlist, documentado
en [OpenAPI](./openapi.json). S/A reciben métricas, calidad, incidencias y filas
administrativas mínimas del dashboard. O **no ejecuta** las consultas de ocupación
ni total Personas; recibe solo incidencias de hoy y tres campos de movimiento
reducido. Su `generado_en` también se redondea a la hora para no exponer instantes
exactos. Sin filtros personales o de fecha en este endpoint.

400 parámetros, 401 sin sesión, 403 rol/transporte denegado, 503 consulta o sesión
indisponible con mensaje mínimo. Error no equivale a cero. No hay caché compartida,
JWT, registro público, cambios IAM, operaciones Edge ni persistencia biométrica.

## Verificación y límites

[Pruebas nuevas](./tests/unit/test_dashboard_0010.py): fórmulas/cortes/empates,
incidencias, rechazos, nocturno, múltiples Puntos, inactivos, sin historia,
base vacía, replay, máximo diez, perfil O/DTO/HTTP, fallos y compilación MySQL
sin conexión. La prueba histórica de estructura 0009 conserva su hash de rutas
preexistentes filtrando **solo** el nuevo Blueprint y exige exactamente una
nueva ruta GET; firma física de once tablas intacta.

Los resultados realmente ejecutados, incluidos fallos iniciales corregidos,
comandos y límites figuran en informes externos de P0. No se ejecutó integración
MySQL ni migración; no se instalaron paquetes o browsers ni se escribió Git.
La autorrevisión no sustituye la revisión independiente posterior.
