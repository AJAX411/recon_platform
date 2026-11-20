# Arquitectura observada — candidata local del Incremento 0010

Se conserva el monolito modular por seis capacidades, organizado directamente
en archivos de responsabilidad según la
[ADR-D0-BE-01](../../backend/ADR_D0_BE_01_ORGANIZACION_CAPACIDADES.md).
No se volvió a ejecutar el traslado C1/C2: ya estaba realizado. El baseline
funcional sigue siendo Contexto Maestro v1.7 con refinamientos aprobados por ámbito.

| Capacidad | Entrada y aplicación | Persistencia y contratos |
|---|---|---|
| [Identidad](../../backend/src/recon_platform/identidad/) | controlador_auth/usuarios, dto_auth/usuarios, servicio_cuentas/sesiones, seguridad_http | modelos, repositorio_cuentas/sesiones, contratos_cuentas/sesiones, unidad_trabajo; CLI explícita |
| [Personas](../../backend/src/recon_platform/personas/) | controlador, dto, servicio, persona, tipo_persona, tipos_documento | modelos, repositorio, contratos, contratos_consultas, lecturas, unidad_trabajo |
| [Accesos](../../backend/src/recon_platform/accesos/) | controlador_puntos/eventos, dto_puntos/eventos, servicio_puntos/eventos, entidades | modelos_puntos/eventos, repositorio_puntos/eventos, contratos por función, lecturas, unidad_trabajo_eventos |
| [Consultas](../../backend/src/recon_platform/consultas/) | controlador, dto, servicio | contratos y unidad_lectura; sin tabla propia, usa contratos públicos de lectura |
| [Auditoría](../../backend/src/recon_platform/auditoria/) | controlador, dto, servicio, evento_auditoria | modelos, repositorio, contratos y unidad_trabajo |
| [Integración Edge administrativa](../../backend/src/recon_platform/integracion_edge/) | controlador, dto, servicio, dispositivo_edge | modelos, repositorio y contratos; metadatos, sin pipeline físico |

La [factory](../../backend/src/recon_platform/__init__.py) registra ocho blueprints.
[Composición](../../backend/src/recon_platform/composicion.py) construye adaptadores
por petición con sesión compartida. Los servicios y entidades no importan Flask,
SQLAlchemy ni repositorios concretos. Los repositorios no hacen commits autónomos;
las unidades de trabajo coordinadas por el caso de uso conservan commit/rollback.
Existen joins/bloqueos ORM cruzados preexistentes en adaptadores, no un dominio
de reconocimiento facial mezclado con login. No se ocultan como desacoplamiento total.

Contratos separados de consultas/persistencia y cuentas/sesiones evitan fusionar
interfaces de semántica distinta. Accesos contiene dos subcapacidades reales
(Puntos y Eventos); mantener archivos con sufijo es proporcional y más claro que
fusionarlos en un controlador gigante. Consultas no necesita un `modelos.py`
vacío para cumplir una plantilla.

En el corte A/D se inventariaron81 módulos y37 subdirectorios antiguos vacíos
o con caché, sin fuentes/wrappers activos. Entonces eran candidatos a retiro,
no se eliminaron en A/D. Macro E retiró únicamente esas rutas verificadas, con
copia externa de cachés y sin borrar módulos; las capas lógicas se conservan. Los .pyc ignorados no son fuentes
canónicas y no deben usarse como entrada de empaquetado. Las exclusiones de
[.dockerignore](../../.dockerignore) los dejan fuera del contexto futuro.

## Frontend

La raíz [frontend/src](../../frontend/src/) usa páginas y componentes DOM,
router con History API, estados en memoria y fetch centralizado. Vite sirve para
desarrollo/build, Bootstrap se importa localmente y React está fuera del grafo
productivo. Se conservan 19 rutas, roles, sesiones y CSRF.

El menú Perfil es lectura de la sesión, sin módulo editable ficticio. Las
confirmaciones de Persona muestran solo los valores administrativos que se
enviarán y bloquean el doble envío. El resumen se invalida al mutar, relee al
volver a Inicio y revalida al refocalizar tras al menos 30 s, sin polling.

El componente selector de Puntos conserva su búsqueda opcional en Registro
manual; en alta Edge solo muestra el desplegable asíncrono paginado después
de Código/Nombre/Modo, sin asociación inferida. La eliminación de datos requiere
una decisión funcional adicional y no se equipara a `estado=INACTIVO`.

## Respaldos locales no publicados

La copia React permanece en `frontend/legacy-react/INC0010_G5_20261119_172819` y la
candidata histórica en `frontend/vanilla-candidato`. Ninguna se elimina, se usa
como runtime o se incorpora masivamente al commit. Sus 94 y 55 archivos fuente
locales, respectivamente, se conservaron por hash al preparar Macro C; sus
dependencias/salidas generadas también se dejan en disco. El historial Git anterior
y los respaldos externos conservan trazabilidad; un clon nuevo usa solo la SPA
canónica. Esos directorios locales no se presuponen presentes en GitHub/Azure.

`.gitignore` excluye esos árboles y los artefactos autogenerados. La configuración
de VS Code oculta los ignorados únicamente en este workspace; no borra archivos
ni modifica ajustes globales. Se pueden abrir manualmente cuando haga falta.

## Dependencias y atribuciones

Bootstrap 5.3.8 declara licencia MIT; conservar sus avisos al compilar/distribuir.
Los iconos usados son SVG inline del módulo local de iconos, sin imágenes faciales
ni descargas de activos en runtime. No se incorporan capturas del profesor como
activos de la aplicación. Su ejemplo orienta aspectos técnicos/visuales, sin
copiar dominio, roles ni mecanismos de seguridad. No se deduce de ello una licencia
global nueva del proyecto ni se redistribuyen materiales privados académicos.

## Evaluación Macro D — organización conservada

La inspección de los 81 módulos y sus imports estáticos no detectó ciclos.
En el corte D, las37 carpetas antiguas conservaban únicamente caché o estaban vacías;
no eran una segunda implementación. EnD no se trasladaron ni eliminaron para simular
una nueva arquitectura. La matriz externa documenta por módulo responsabilidad,
capa lógica, dependencias entrantes/salientes y referencias de pruebas; ese
análisis estático no equivale a cobertura dinámica ni demuestra desacoplamiento
absoluto de los adaptadores ORM con joins cruzados preexistentes.

Macro D expone el caso de uso existente CambiarLoginUsuario mediante un PATCH
mínimo en el controlador IAM. No mueve dominio, ORM, repositorios, composición
ni migraciones. El guard SUPERADMIN/CSRF, los contratos de cuentas, la unidad de
trabajo y la auditoría conservan sus responsabilidades. El frontend separa la
edición de login de los cambios de rol y estado; no añade nombres o FK Persona.
La integración MySQL real del PATCH queda pendiente de autorización y prueba.

## Macro E — higiene y explicación

Las37 carpetas antiguas se retiraron tras comprobar vacío o caché ignorada, con copia externa de la caché y sin borrar fuentes. Los81 módulos mantienen sus rutas. [Guía de lectura](./GUIA_LECTURA_CODIGO.md) y [guion de sustentación](./GUIA_SUSTENTACION_CODIGO.md) explican las capas lógicas existentes. No se hizo reorganización de módulos.
