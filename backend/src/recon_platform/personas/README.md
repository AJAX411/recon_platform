# Personas — Proyecto Recon Facial

La capacidad administra información funcional de Persona dentro del monolito
modular. La arquitectura y las reglas conservan su estado **PROVISIONAL** según
el Contexto Maestro v1.7 OFICIAL y las resoluciones aplicables. Persona es
independiente de UsuarioPlataforma: no existe FK ni vinculación automática.

## Organización implementada localmente en 0009

| Grupo | Código canónico |
|---|---|
| Controlador HTTP | [personas](./controladores/personas.py) |
| DTO de entrada/salida | [validadores y representación](./dto/personas.py) |
| Servicios/casos de uso | [RegistrarPersona, ConsultarPersona y AdministrarPersonas](./servicios/personas.py) |
| Puertos | [repositorios y unidad de trabajo](./puertos/personas.py) |
| Dominio | [Persona](./dominio/persona.py), [TipoPersona](./dominio/tipo_persona.py) |
| Infraestructura | [modelos](./infraestructura/modelos.py), [repositorios](./infraestructura/repositorios.py), [UoW](./infraestructura/unidad_trabajo.py) |

El controlador usa AdministrarPersonas para conservar permisos y auditoría.
Los repositorios no confirman por su cuenta; el caso de uso controla la
transacción completa. La [composición](../composicion.py) construye las
dependencias con la sesión compartida. La validación DTO conserva las
diferencias entre forma HTTP, campos nullable y reglas del dominio.

Las seis operaciones HTTP existentes requieren SUPERADMIN o ADMINISTRADOR;
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

Permanecen pendientes el catálogo documental definitivo, reglas condicionales
de categorías no resueltas, el vínculo futuro con cuentas y las políticas de
enrolamiento e integración biométrica. Personas no depende de cámara, Hailo,
ONNX, fotografías, embeddings ni plantillas. RegistrarPersona no completa por
sí solo CU-03. El Bloque 3 y la revisión independiente de 0009 son posteriores.
