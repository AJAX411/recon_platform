# Personas — Proyecto Recon Facial

La capacidad administra información funcional de Persona dentro del monolito
modular. La arquitectura y las reglas conservan su estado **PROVISIONAL** según
el Contexto Maestro v1.7 OFICIAL y las resoluciones aplicables. Persona es
independiente de UsuarioPlataforma: no existe FK ni vinculación automática.

## Organización refinada por ADR-D0-BE-01 (Macrobloque C)

El responsable aprobó el refinamiento físico de 0009 el 18/11/2026. Se mantienen
las responsabilidades; los módulos residen directamente dentro de Personas.

| Grupo | Código canónico |
|---|---|
| Controlador HTTP | [controlador](./controlador.py) |
| DTO de entrada/salida | [validadores y representación](./dto.py) |
| Servicios/casos de uso | [RegistrarPersona, ConsultarPersona y AdministrarPersonas](./servicio.py) |
| Contratos de persistencia | [repositorios y unidad de trabajo](./contratos.py) |
| Contrato público de consultas | [LecturaPersonas](./contratos_consultas.py) |
| Dominio | [Persona](./persona.py), [TipoPersona](./tipo_persona.py) |
| Persistencia y lecturas | [modelos](./modelos.py), [repositorio](./repositorio.py), [UoW](./unidad_trabajo.py), [agregado](./lecturas.py) |

Recorrido real: HTTP → guard IAM/CSRF → DTO → AdministrarPersonas → contratos
de repositorio/UoW → adaptadores SQLAlchemy → DTO/respuesta. El servicio depende
de dominio y contratos; composición inyecta los adaptadores, no al revés.
Consultas usa LecturaPersonas sin importar el repositorio privado.

El controlador usa AdministrarPersonas para conservar permisos y auditoría.
Los repositorios no confirman por su cuenta; el caso de uso controla la
transacción completa. La [composición](../composicion.py) construye las
dependencias con la sesión compartida. La validación DTO conserva las
diferencias entre forma HTTP, campos nullable y reglas del dominio.

Las siete operaciones HTTP actuales requieren SUPERADMIN o ADMINISTRADOR;
POST y PATCH requieren CSRF. El listado conserva paginación y filtros exactos.
Las escrituras exitosas registran actor, Persona y fecha UTC en la misma
transacción. ACTIVO no significa enrolamiento válido ni autorización física.

## Historia y límites

Este documento se originó con el baseline v1.5 y la preparación de persistencia
y API de Personas. Las afirmaciones antiguas sobre migraciones preparadas/no
aplicadas corresponden a aquellos incrementos. En 0009 no se consultó ninguna
base real ni se aplicaron migraciones; el [README backend](../../../README.md)
conserva los resultados históricos reportados y el cruce de rutas retiradas.
La reorganización local y sus pruebas figuran en el
[manifiesto 0009](../../../INCREMENTO_0009_ESTRUCTURA_UNIFORME.md).

## Catálogo documental P1-B — 17/11/2026

El responsable ratificó los códigos internos CC, TI, CE, PA, PPT y RC, todos
habilitados y en ese orden. [Catálogo](./tipos_documento.py) inmutable
de aplicación; no es TipoPersona, no crea tabla/migración ni política legal.
GET `/api/v1/personas/tipos-documento` devuelve código, nombre y habilitación,
solo S/A, no-store; query extra 400 y guardas/errores actuales.

Ambas altas exigen un código habilitado; al editar, solo el cambio efectivo del
par tipo/número exige nueva asignación habilitada. Omitir o reenviar par idéntico
conserva legado bajo reglas vigentes. Lectura/filtro/hidratación siguen abiertos
a valores históricos. No nuevas normalizaciones; se conserva trim exterior.
La regla TipoPersona ACTIVO al actualizar permanece incluso si PATCH lo omite;
no confundirla con activar/desactivar Persona. Campos de respuesta intactos.
Este estrechamiento de entradas está aprobado y descrito en
[especificación P1-B](../../../INCREMENTO_0010_P1B.md) y
[OpenAPI](../../../openapi.json). Correo aplazado, sin modificación física.

Permanecen pendientes las reglas condicionales
de categorías no resueltas, el vínculo futuro con cuentas y las políticas de
enrolamiento e integración biométrica. Personas no depende de cámara, Hailo,
ONNX, fotografías, embeddings ni plantillas. RegistrarPersona no completa por
sí solo CU-03. P1-B local se entrega para revisión independiente; pruebas
aisladas no cierran las reservas de MySQL/web ni el Incremento 0010.
