# Backend — Proyecto Recon Facial

Backend de la plataforma web del Proyecto Recon Facial.

## Incremento 0009 — organización local del backend

La estructura B controlada se implementó localmente en el Bloque 2 autorizado
el 14/11/2026. Se conservan el monolito modular por capacidades, el Contexto
Maestro v1.7 OFICIAL y los estados de sus resoluciones. El resultado y las
verificaciones están en el [manifiesto 0009](./INCREMENTO_0009_ESTRUCTURA_UNIFORME.md).
El Bloque 3 y la revisión independiente están pendientes. Las referencias
operativas y resultados de otros incrementos que siguen abajo son históricos;
esta reorganización no certifica el estado actual de una base MySQL.

Cada capacidad existente —Identidad, Personas, Accesos, Integración Edge
administrativa y Auditoría— contiene los mismos grupos de responsabilidades:

| Grupo | Responsabilidad |
|---|---|
| Controladores | HTTP, JSON, códigos, cabeceras, filtros y guards |
| DTO | Funciones explícitas de validación de forma y representación acotada |
| Servicios | Casos de uso existentes, reglas de aplicación y transacciones |
| Puertos | Contratos de persistencia y colaboración requeridos por los servicios |
| Dominio | Entidades y reglas, independientes de Flask y SQLAlchemy |
| Infraestructura | Modelos ORM, repositorios y unidades de trabajo existentes |

La [fábrica](./src/recon_platform/__init__.py) registra los mismos siete
Blueprints. [Composición](./src/recon_platform/composicion.py) construye los
adaptadores y casos por petición con la misma `db.session`; recibe explícitamente
la clave CSRF y los relojes cuando corresponde. No importa controladores ni
confirma transacciones. El adaptador [seguridad HTTP](./src/recon_platform/identidad/controladores/seguridad.py)
conserva CSRF, transporte, roles y el único reloj IAM `ahora_utc`. Autenticación
consulta ese atributo desde el módulo; Eventos conserva su reloj `_reloj`,
que pasa como callable a composición.

Ejemplos para recorrer el código:

- Personas: [controlador](./src/recon_platform/personas/controladores/personas.py)
  → [DTO](./src/recon_platform/personas/dto/personas.py) →
  [AdministrarPersonas](./src/recon_platform/personas/servicios/personas.py)
  → puertos/dominio → repositorios/modelos/UoW. La escritura y su auditoría se
  confirman juntas; registrar administrativamente no completa el CU-03 biométrico.
- Login: [autenticación](./src/recon_platform/identidad/controladores/autenticacion.py)
  → seguridad/composición → [GestionSesiones](./src/recon_platform/identidad/servicios/sesiones.py)
  y [cuentas](./src/recon_platform/identidad/servicios/cuentas.py). Se conservan
  las fases de verificación de credenciales y rotación de sesión existentes.
- Manual: [controlador de Eventos](./src/recon_platform/accesos/controladores/eventos.py)
  → DTO/composición → [RegistrarEventoManual](./src/recon_platform/accesos/servicios/eventos.py)
  → repositorios/UoW. Se conservan inicio limpio, revalidación, coordinación por
  Persona, idempotencia, jornada Bogotá, auditoría y respuestas 201/200.

Se conservan las proyecciones de consultas de Eventos en su
[repositorio](./src/recon_platform/accesos/infraestructura/repositorios_eventos.py),
incluida la minimización de OPERADOR. También se conserva la obtención interna
del contexto de fallo de modo en el controlador de Dispositivos. Esos
acoplamientos quedan documentados; no se rediseñaron en 0009. No se añadieron
servicios delegadores, tablas, dependencias, frontend o integración facial/Edge.

### Rutas históricas del corte 2180476

Los orígenes retirados se relacionan abajo con las rutas canónicas. Los enlaces
históricos de los manifiestos frontend 0008 se conservan como evidencia del
corte original; algunos dejaron de resolver sobre este checkout. Esta tabla
permite localizar el código actual, sin afirmar que aquellos enlaces siguen
navegables. El contenido original puede consultarse con Git de lectura.

| Origen hist?rico bajo `src/recon_platform` | Destino can?nico bajo el mismo directorio |
|---|---|
| `accesos/api.py` | [accesos/controladores/puntos.py](./src/recon_platform/accesos/controladores/puntos.py); [accesos/dto/puntos.py](./src/recon_platform/accesos/dto/puntos.py) |
| `accesos/aplicacion.py` | [accesos/puertos/puntos.py](./src/recon_platform/accesos/puertos/puntos.py); [accesos/servicios/puntos.py](./src/recon_platform/accesos/servicios/puntos.py) |
| `accesos/dominio.py` | [accesos/dominio/punto_acceso.py](./src/recon_platform/accesos/dominio/punto_acceso.py) |
| `accesos/eventos_api.py` | [accesos/controladores/eventos.py](./src/recon_platform/accesos/controladores/eventos.py); [accesos/dto/eventos.py](./src/recon_platform/accesos/dto/eventos.py); [composicion.py](./src/recon_platform/composicion.py) |
| `accesos/eventos_aplicacion.py` | [accesos/puertos/eventos.py](./src/recon_platform/accesos/puertos/eventos.py); [accesos/servicios/eventos.py](./src/recon_platform/accesos/servicios/eventos.py) |
| `accesos/eventos_dominio.py` | [accesos/dominio/evento_acceso.py](./src/recon_platform/accesos/dominio/evento_acceso.py) |
| `accesos/eventos_infraestructura.py` | [accesos/infraestructura/modelos_eventos.py](./src/recon_platform/accesos/infraestructura/modelos_eventos.py); [accesos/infraestructura/repositorios_eventos.py](./src/recon_platform/accesos/infraestructura/repositorios_eventos.py); [accesos/infraestructura/unidad_trabajo_eventos.py](./src/recon_platform/accesos/infraestructura/unidad_trabajo_eventos.py) |
| `accesos/infraestructura.py` | [accesos/infraestructura/modelos_puntos.py](./src/recon_platform/accesos/infraestructura/modelos_puntos.py); [accesos/infraestructura/repositorios_puntos.py](./src/recon_platform/accesos/infraestructura/repositorios_puntos.py) |
| `auditoria/api.py` | [auditoria/controladores/eventos.py](./src/recon_platform/auditoria/controladores/eventos.py); [auditoria/dto/eventos.py](./src/recon_platform/auditoria/dto/eventos.py) |
| `auditoria/aplicacion.py` | [auditoria/puertos/eventos.py](./src/recon_platform/auditoria/puertos/eventos.py); [auditoria/servicios/eventos.py](./src/recon_platform/auditoria/servicios/eventos.py) |
| `auditoria/dominio.py` | [auditoria/dominio/evento_auditoria.py](./src/recon_platform/auditoria/dominio/evento_auditoria.py) |
| `auditoria/infraestructura.py` | [auditoria/infraestructura/modelos.py](./src/recon_platform/auditoria/infraestructura/modelos.py); [auditoria/infraestructura/repositorios.py](./src/recon_platform/auditoria/infraestructura/repositorios.py); [auditoria/infraestructura/unidad_trabajo.py](./src/recon_platform/auditoria/infraestructura/unidad_trabajo.py) |
| `composicion_administrativa.py` | [composicion.py](./src/recon_platform/composicion.py) |
| `http_administrativo.py` | [http/administrativo.py](./src/recon_platform/http/administrativo.py) |
| `identidad/administracion_api.py` | [composicion.py](./src/recon_platform/composicion.py); [identidad/controladores/usuarios.py](./src/recon_platform/identidad/controladores/usuarios.py); [identidad/dto/usuarios.py](./src/recon_platform/identidad/dto/usuarios.py) |
| `identidad/api.py` | [composicion.py](./src/recon_platform/composicion.py); [identidad/controladores/autenticacion.py](./src/recon_platform/identidad/controladores/autenticacion.py); [identidad/controladores/seguridad.py](./src/recon_platform/identidad/controladores/seguridad.py); [identidad/dto/autenticacion.py](./src/recon_platform/identidad/dto/autenticacion.py) |
| `identidad/aplicacion/casos_de_uso.py` | [identidad/servicios/cuentas.py](./src/recon_platform/identidad/servicios/cuentas.py) |
| `identidad/aplicacion/limitador.py` | [identidad/servicios/limitador.py](./src/recon_platform/identidad/servicios/limitador.py) |
| `identidad/aplicacion/puertos.py` | [identidad/puertos/cuentas.py](./src/recon_platform/identidad/puertos/cuentas.py) |
| `identidad/aplicacion/sesiones.py` | [identidad/puertos/sesiones.py](./src/recon_platform/identidad/puertos/sesiones.py); [identidad/servicios/sesiones.py](./src/recon_platform/identidad/servicios/sesiones.py) |
| `identidad/infraestructura/sesiones.py` | [identidad/infraestructura/repositorios_sesiones.py](./src/recon_platform/identidad/infraestructura/repositorios_sesiones.py) |
| `integracion_edge/api.py` | [integracion_edge/controladores/dispositivos.py](./src/recon_platform/integracion_edge/controladores/dispositivos.py); [integracion_edge/dto/dispositivos.py](./src/recon_platform/integracion_edge/dto/dispositivos.py) |
| `integracion_edge/aplicacion.py` | [integracion_edge/puertos/dispositivos.py](./src/recon_platform/integracion_edge/puertos/dispositivos.py); [integracion_edge/servicios/dispositivos.py](./src/recon_platform/integracion_edge/servicios/dispositivos.py) |
| `integracion_edge/dominio.py` | [integracion_edge/dominio/dispositivo_edge.py](./src/recon_platform/integracion_edge/dominio/dispositivo_edge.py) |
| `integracion_edge/infraestructura.py` | [integracion_edge/infraestructura/modelos.py](./src/recon_platform/integracion_edge/infraestructura/modelos.py); [integracion_edge/infraestructura/repositorios.py](./src/recon_platform/integracion_edge/infraestructura/repositorios.py) |
| `personas/api.py` | [composicion.py](./src/recon_platform/composicion.py); [personas/controladores/personas.py](./src/recon_platform/personas/controladores/personas.py); [personas/dto/personas.py](./src/recon_platform/personas/dto/personas.py) |
| `personas/aplicacion/casos_de_uso.py` | [personas/servicios/personas.py](./src/recon_platform/personas/servicios/personas.py) |
| `personas/aplicacion/puertos.py` | [personas/puertos/personas.py](./src/recon_platform/personas/puertos/personas.py) |
| `identidad/aplicacion/__init__.py`, `personas/aplicacion/__init__.py` | Retirados al quedar sin consumidores; servicios y puertos tienen paquetes propios. |

## Alcance implementado

La fábrica Flask conserva la ruta temporal `/_diagnostico`. El módulo Personas
dispone de entidades de dominio, casos de uso internos `RegistrarPersona` y
`ConsultarPersona` y repositorios SQLAlchemy. La migración `0001_personas` fue
aplicada y verificada manualmente en `recon_tests` y `recon_dev`; el responsable
informó 10 pruebas de integración MySQL aprobadas y persistencia comprobada en
desarrollo. Son resultados históricos, no una ejecución de este incremento.
El registro administrativo es una parte de CU-03/HU-04; no completa esos casos de uso.
La API HTTP administrativa de Personas ya está implementada. Según la
validación reportada por el responsable, `0004_auditoria_personas` fue aplicada
a `recon_tests` y `recon_dev`. Las 26 pruebas de integración MySQL anteriores
se ejecutaron de nuevo dentro de la suite de 35 pruebas del incremento 0005,
según los resultados comunicados por el responsable.
Los permisos SUPERADMIN/ADMINISTRADOR, los filtros y el contrato HTTP son
decisiones PROVISIONALES de este encargo. La API no implementa enrolamiento
facial; no completa CU-03.

Identity/IAM incorpora Rol, UsuarioPlataforma independiente de Persona, casos
de uso administrativos exclusivos de SUPERADMIN, verificación de credenciales,
auditoría de operaciones exitosas y un comando explícito de bootstrap. La
migración `0002_identity_iam` fue aplicada y verificada en ambas bases por el
responsable. La primera cuenta SUPERADMIN existe en desarrollo. El incremento
anterior añadió endpoints de autenticación y administración IAM, sin registro
público. `0003_sesiones_iam` fue aplicada y validada en
`recon_tests` y `recon_dev`, según las ejecuciones reportadas por el responsable.

Organización provisional: API/presentación → aplicación/casos de uso →
dominio/reglas → infraestructura/persistencia. El dominio no importa el ORM.

## Incremento 0005 — administración de puntos, dispositivos y auditoría general

Las capacidades `accesos`, `integracion_edge` y `auditoria` implementan,
respectivamente, `PuntoAcceso`, la administración web de `DispositivoEdge` y
`EventoAuditoria` mínima. La administración Edge no comunica con Raspberry Pi.
Las rutas bajo `/api/v1/puntos-acceso` y `/api/v1/dispositivos-edge` permiten
crear, consultar, listar, editar los campos permitidos y cambiar estado; el
dispositivo también permite cambiar `modo_operacion`. Código y asociación al
punto son inmutables después de crear. La API no acepta cambios administrativos
de `ultima_comunicacion`. `GET /api/v1/auditoria/eventos` ofrece consulta
paginada y filtrada; no hay endpoints de escritura general de eventos.

Los tres roles consultan puntos y dispositivos y cambian estado y modo.
SUPERADMIN y ADMINISTRADOR crean y editan nombre/descripción permitidos y
consultan la auditoría general. Una operación exitosa confirma la mutación y
su evento en la misma transacción. Tras un rechazo administrativo relevante,
se revierte la operación y se guarda un evento `FALLIDO` independiente; no se
auditan en masa los rechazos de autenticación, CSRF o infraestructura. Las
auditorías especializadas de IAM y Personas permanecen intactas. En cambios de
modo se conserva el valor anterior y el nuevo sin almacenar payloads sensibles.

[`migrations/versions/0005_puntos_edge_auditoria.py`](./migrations/versions/0005_puntos_edge_auditoria.py)
fue aplicada y verificada en `recon_tests` y `recon_dev`, según los resultados
comunicados por el responsable. Ambos procedimientos generaron respaldos
privados fuera del repositorio. La revisión crea tres tablas InnoDB con PK
`INT UNSIGNED`, FK, unicidades, CHECK, índices y fechas `DATETIME`
convencionales UTC; no altera tablas previas.
Los procedimientos utilizados se conservan para trazabilidad y requieren una
nueva revisión antes de cualquier repetición:

- [`scripts/verificar_recon_tests_0005.py`](./scripts/verificar_recon_tests_0005.py)
  y [`scripts/verificar_recon_dev_0005.py`](./scripts/verificar_recon_dev_0005.py):
  comprobaciones de solo lectura de identidad, revisión, estructura y datos.
- [`scripts/verificar_objetos_recon_tests_0005.py`](./scripts/verificar_objetos_recon_tests_0005.py):
  acredita con cuenta administrativa independiente la ausencia de rutinas,
  eventos y triggers antes de excluirlos del respaldo de pruebas.
- [`scripts/aplicar_0005_recon_tests.sh`](./scripts/aplicar_0005_recon_tests.sh)
  y [`scripts/aplicar_0005_recon_dev.sh`](./scripts/aplicar_0005_recon_dev.sh):
  se ejecutaron bajo control del responsable con preflight, respaldo privado,
  confirmación literal y comprobación posterior, según su reporte.
- [`scripts/probar_0005_recon_tests.sh`](./scripts/probar_0005_recon_tests.sh):
  permitió ejecutar la suite MySQL contra `recon_tests` verificada en 0005;
  el verificador posterior terminó satisfactoriamente sin residuos detectados,
  según el responsable.

Codex ejecutó la suite unitaria local con 195 pruebas aprobadas
(`python -B -m pytest -p no:cacheprovider tests/unit -q`). El responsable
informó 35 pruebas de integración MySQL aprobadas en `recon_tests`: las nueve
del nuevo módulo y las 26 anteriores. La revisión independiente fue favorable.
Codex no ejecutó las pruebas MySQL ni aplicó migraciones reales.
En el cierre de 0005 no se habían implementado `EventoAcceso`, observaciones biométricas, conectividad,
alternancia funcional AUTOMATICO, frontend ni reasignación de dispositivos.
El catálogo final de auditoría y su retención siguen PENDIENTES.

## Entorno

El desarrollo utiliza un entorno virtual local ubicado en:

`.venv/`

Las credenciales y secretos reales deben almacenarse en `.env`,
archivo que no debe versionarse.

`.env.example` sirve únicamente como plantilla segura de configuración. La
aplicación lee variables del entorno del proceso; no carga `.env` automáticamente.

Para desarrollo, configurar `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y
`DB_PASSWORD`. Para `create_app(pruebas=True)`, configurar además
`DB_TEST_NAME`, `DB_TEST_USER` y `DB_TEST_PASSWORD`. La aplicación exige el
nombre de la base de desarrollo para comprobar que ambas bases sean distintas,
pero nunca usa las credenciales de desarrollo como alternativa en pruebas.
`DB_HOST` y `DB_PORT` son comunes a ambos modos y se usa `utf8mb4`.
Sin configuración de desarrollo, la fábrica permite solamente la ruta
diagnóstica. En modo de pruebas, la falta de cualquier valor requerido produce
un error antes de abrir conexión, sin revelar contraseñas ni URLs.

Las unidades de trabajo confirman o revierten la operación completa; los
repositorios no hacen commits. Los modelos guardan `DATETIME` en UTC por
convención y devuelven fechas con zona UTC al dominio. Las restricciones de
unicidad y la FK también se declaran en la migración para proteger concurrencia
e integridad referencial. El catálogo inicial de seis TipoPersona se carga allí.

Las pruebas unitarias se ejecutan desde `backend/` con el entorno virtual
existente: `python -B -m pytest -p no:cacheprovider tests/unit`. Estas pruebas
no abren MySQL.

## Identity/IAM: bootstrap controlado

La resolución puntual **Independencia entre UsuarioPlataforma y Persona**
(15/10/2026, PROVISIONAL — APROBADA PARA IMPLEMENTACIÓN) sustituye en su ámbito
la vinculación obligatoria del Contexto Maestro v1.5. La cuenta no contiene
`id_persona`; la vinculación y su cardinalidad futuras permanecen PENDIENTES.
Cada cuenta tiene un Rol con FK obligatoria. El login se normaliza a minúsculas
ASCII y es único. Las contraseñas se almacenan como hash scrypt; el mínimo
técnico inicial es 12 caracteres, mientras la política definitiva sigue
PENDIENTE. El registro de auditoría IAM guarda actor, cuenta afectada, acción,
resultado, momento y cambios no secretos. La auditoría de intentos fallidos y
la política de recuperación requieren un diseño posterior. Esta tabla de
auditoría específica de IAM no define todavía el modelo físico general de
EventoAuditoria del proyecto.

La migración `0002_identity_iam` crea roles y tablas, pero ninguna cuenta ni
contraseña. El responsable ya inicializó la primera cuenta SUPERADMIN en
`recon_dev`. Para una base nueva, tras aprobación y comprobación del destino,
el comando manual desde `backend/` es:

```powershell
& '.\.venv\Scripts\python.exe' -B -m flask --app recon_platform:create_app bootstrap-superadmin
```

El comando exige confirmar el destino previsto y solicita login y contraseña
con entrada oculta y confirmación; no acepta la contraseña como argumento. Si
ya existe una cuenta SUPERADMIN, no
crea otra. No se ejecuta al importar ni al iniciar Flask. Comprobar el destino
de la conexión antes de invocarlo. El incremento HTTP no ejecuta ese comando.

## Integración MySQL con activación explícita

Pytest descubre únicamente `tests/unit` por defecto. Las pruebas en
`tests/integration` requieren además `RECON_RUN_MYSQL_INTEGRATION=1`; sin esa
variable se omiten incluso si se selecciona la carpeta expresamente. La
aplicación no carga `.env` automáticamente: quien ejecute las pruebas debe
proporcionar las variables al proceso sin imprimir las contraseñas.

Antes de cada conexión de prueba se exige `mysql+pymysql` hacia
`127.0.0.1:3306`, base `recon_tests` y usuario `recon_test_app`. Se consulta
también la identidad real de la conexión, una revisión conocida de Alembic
(`0001_personas`, `0002_identity_iam`, `0003_sesiones_iam`,
`0004_auditoria_personas` o `0005_puntos_edge_auditoria`) y el motor InnoDB
de las tablas correspondientes. Cualquier fallo detiene la
ejecución antes de las escrituras. Las pruebas no crean ni migran tablas y no
usan `create_all`, `drop_all` ni borrados globales. Cada prueba de datos se
ejecuta en una transacción externa que se revierte al terminar; los commits de
los casos de uso quedan dentro de savepoints. No se eliminan registros ajenos.

Para repetir esas pruebas tras aprobación, comprobar el destino y la revisión
del esquema. Con `DB_NAME`, `DB_TEST_NAME`, `DB_TEST_USER` y
`DB_TEST_PASSWORD` configurados en el entorno del proceso, además de
`DB_HOST=127.0.0.1` y `DB_PORT=3306`, ejecutar desde `backend/`:

```powershell
$env:RECON_RUN_MYSQL_INTEGRATION = "1"
& '.\.venv\Scripts\python.exe' -B -m pytest -p no:cacheprovider tests/integration
Remove-Item Env:RECON_RUN_MYSQL_INTEGRATION
```

El responsable informó 22 pruebas de integración MySQL aprobadas en
`recon_tests` con `0003_sesiones_iam`: 10 de Personas, 8 de Identity/IAM y 4 de
sesiones, incluida la correspondencia SHA-256 del digest persistido. Las
pruebas IAM exigen una revisión IAM conocida (`0002` o `0003`) antes de escribir y
comprueban esquema, roles, ausencia inicial de cuentas, FK, unicidades, casos
de uso y rollback. La comprobación de ausencia de cuentas debe ejecutarse
después de aplicar `0002` y antes del bootstrap operativo. Las cuentas
ficticias de las otras pruebas, incluida la SUPERADMIN de prueba, se crean
dentro de transacciones revertibles; no se invoca el comando de bootstrap.

Para una nueva ejecución autorizada, se pueden seleccionar solo las pruebas IAM
con el mismo entorno y la misma activación explícita:

```powershell
$env:RECON_RUN_MYSQL_INTEGRATION = "1"
& '.\.venv\Scripts\python.exe' -B -m pytest -p no:cacheprovider tests/integration/test_identidad_mysql.py
Remove-Item Env:RECON_RUN_MYSQL_INTEGRATION
```

Las pruebas unitarias no sustituyen esta validación MySQL.

Las pruebas de `tests/integration/test_personas_http_mysql.py` admiten
`0004_auditoria_personas` o `0005_puntos_edge_auditoria`. El responsable informó que las
ejecutó en `recon_tests` tras aplicar y revisar esa migración.
El fixture verifica nombre de base, usuario, puerto, revisión y tablas InnoDB
antes de permitir escrituras; cada prueba revierte su transacción externa.

## Procedimiento 0004 en recon_tests

La auditoría específica de Personas es **PROVISIONAL**. Registra operaciones
humanas exitosas sobre Personas; no sustituye al `EventoAuditoria` lógico
general de v1.5, que también contempla eventos automáticos y actor nullable.
La política general de auditoría y retención continúa PENDIENTE.

[`scripts/verificar_recon_tests_0004.py`](./scripts/verificar_recon_tests_0004.py)
comprueba exclusivamente por lectura la identidad real
`recon_tests`/`recon_test_app`, revisión exacta `0003` antes y `0004` después,
tablas InnoDB, catálogos, restricciones anteriores, nueva tabla, columnas,
tipos, PK, FK con `RESTRICT`, CHECK, índice y ausencia de registros temporales.
Falla cerrado ante cualquier discrepancia. No muestra contraseñas ni URL.

[`scripts/aplicar_0004_recon_tests.sh`](./scripts/aplicar_0004_recon_tests.sh)
se utilizó en `recon_tests`, según el estado confirmado por el responsable. Exige
`RECON_AUTORIZAR_MIGRACION_0004=1`, contraseña introducida de forma
oculta, verificación previa, respaldo privado fuera del repositorio,
confirmación literal y nueva verificación inmediata. Aplica únicamente el
objetivo `0004_auditoria_personas` con la fábrica en modo de pruebas. No debe
usarse para `recon_dev` ni ante un esquema inesperado. Si falla tras comenzar
la migración, se detiene y requiere inspección manual; no intenta restaurar ni
borrar datos automáticamente.

[`scripts/probar_0004_recon_tests.sh`](./scripts/probar_0004_recon_tests.sh)
requiere autorización explícita
`RECON_AUTORIZAR_PRUEBAS_MYSQL_0004=1` y comprobación `0004` antes de activar
las pruebas de integración MySQL. Las pruebas usan transacciones externas con
savepoints y rollback, y el script repite la verificación de ausencia de
residuos al finalizar. Los procedimientos históricos de `0003` se conservan.

## Procedimiento histórico 0004 de recon_dev — ya aplicado según el responsable

[`scripts/verificar_recon_dev_0004.py`](./scripts/verificar_recon_dev_0004.py)
comprueba por lectura la identidad real `recon_dev`/`recon_dev_app`, revisión
exacta `0003` antes y `0004` después, tablas InnoDB, esquema y restricciones
previas, Persona ficticia `id_persona=1`, roles, único SUPERADMIN inicial activo
y su auditoría de bootstrap. Tras `0004`, reutiliza el verificador probado de
la nueva tabla, incluido el CHECK, y exige que `auditoria_personas` esté vacía.
Compara además huellas y cantidades de todas las filas de las seis tablas
preexistentes con un estado privado creado antes del respaldo. El verificador
no modifica MySQL ni muestra filas, contraseñas, hashes o tokens.
Con `--antes --guardar-estado`, primero verifica la conexión, el esquema y los
datos, y después crea el JSON privado con `O_EXCL`, sin sobrescribir un archivo
existente. Los errores distinguen conexión MySQL, validación de esquema/datos y
escritura del estado sin mostrar detalles de excepciones. Un intento histórico
se reportó detenido aquí; posteriormente se confirmó la aplicación de 0004.

[`scripts/aplicar_0004_recon_dev.sh`](./scripts/aplicar_0004_recon_dev.sh)
documenta el procedimiento histórico que requería autorización y revisión.
Exige `RECON_AUTORIZAR_MIGRACION_0004_RECON_DEV=1`, contraseña oculta de
`recon_dev_app`, verificación inicial, respaldo con `mysqldump` y marcadores de
integridad, confirmación literal `APLICAR_0004_RECON_DEV` y segunda verificación
inmediatamente antes de `db upgrade 0004_auditoria_personas`. Comprueba el
resultado y la preservación de las filas anteriores. El respaldo y el estado
quedan en una carpeta privada de `~/ReconFacialBackups`, fuera del repositorio.
La aplicación debe estar detenida y no debe haber escrituras concurrentes;
de otro modo la comparación de datos detendrá el procedimiento. Un fallo exige
inspección manual; el script no restaura, elimina ni reintenta automáticamente.

El intento anterior se detuvo durante `mysqldump`, antes de confirmar o migrar:
`--events` exige el privilegio `EVENT` de `recon_dev`; `--routines` exige
privilegios de lectura global para el volcado. No se amplían los permisos de
`recon_dev_app`. `mysqldump` también requiere `TRIGGER` para volcar triggers.
El procedimiento usa `--skip-events --skip-routines --skip-triggers` para
respaldar tablas y filas con esa cuenta. Ese respaldo solo cubre todos los
objetos de `recon_dev` si se acredita que no existen eventos, rutinas ni triggers.
Las comprobaciones administrativas históricas comunicaron cero en las tres
categorías; el procedimiento no presume que el estado siga igual.

[`scripts/verificar_objetos_recon_dev_0004.py`](./scripts/verificar_objetos_recon_dev_0004.py)
realiza esa comprobación de solo lectura con una cuenta administrativa distinta,
antes del respaldo y otra vez antes de migrar. Fija `127.0.0.1:3306/recon_dev`,
contrasta la identidad real, examina `SHOW GRANTS FOR CURRENT_USER()` y exige
concesiones directas que permitan ver **todas** las rutinas (global `SELECT` o
`SHOW_ROUTINE`), **todos** los eventos (`EVENT` global o sobre `recon_dev`) y
**todos** los triggers (`TRIGGER` global o sobre todo `recon_dev`). Un permiso
`TRIGGER` limitado a algunas tablas no acredita visibilidad completa. Después
exige cero filas para `recon_dev` en `INFORMATION_SCHEMA.ROUTINES`,
`INFORMATION_SCHEMA.EVENTS` y `INFORMATION_SCHEMA.TRIGGERS`. Una lista vacía
sin esos privilegios, un conteo ambiguo o una revocación detienen el proceso.
También se detiene si existe cualquier objeto de esas categorías; en ese caso
se necesita otro plan de respaldo que lo incluya.
La contraseña administrativa se pide oculta y solo se pasa al verificador, nunca
a `mysqldump`, Flask ni a la salida. No se cambian permisos MySQL.

Para revisar independientemente la premisa, la cuenta administrativa debe
ejecutar consultas de solo lectura en `recon_dev` y comprobar identidad,
concesiones y los tres conteos antes de aceptar la exclusión:

```sql
SELECT DATABASE(), CURRENT_USER(), USER(), @@port;
SHOW GRANTS FOR CURRENT_USER();
SELECT COUNT(*) FROM information_schema.EVENTS WHERE EVENT_SCHEMA = 'recon_dev';
SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA = 'recon_dev';
SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = 'recon_dev';
```

No usar el resultado de una cuenta con visibilidad parcial. Conservar para
inspección el respaldo parcial del intento detenido; no restaurarlo ni borrarlo
como parte de esta corrección.

Tras la autorización posterior, la invocación prevista desde Git Bash y
`backend/` es:

```bash
RECON_AUTORIZAR_MIGRACION_0004_RECON_DEV=1 bash scripts/aplicar_0004_recon_dev.sh
```

El texto de este apartado describe 0004, no una operación pendiente del
incremento actual. Para 0005 se usan los verificadores y scripts indicados
arriba, previa revisión y autorización independiente.

## Autenticación HTTP humana — decisión de implementación del prototipo

El contrato provisional está en [`openapi.json`](./openapi.json). La resolución
Identity/IAM mantiene sesiones del lado del servidor; para este incremento se
aprobó guardarlas en MySQL mediante `0003_sesiones_iam`, sin alterar `0001` ni
`0002`. La tabla guarda solo el digest SHA-256 del identificador opaco, el ID de
la cuenta, fechas UTC y revocación. También admite una sesión anónima temporal
para obtener CSRF antes del login. Cada sesión se revoca de forma independiente.

La cookie `recon_session` es `HttpOnly`, `SameSite=Lax`, limitada a `/api/v1` y
`Secure` por defecto. Para usar HTTP **solo en desarrollo local**, configurar
`RECON_LOCAL_HTTP=1` y `RECON_SESSION_COOKIE_SECURE=0`, con `DB_HOST=127.0.0.1`
y Flask escuchando únicamente en `127.0.0.1`. Fuera de ese caso se requiere
HTTPS para que el navegador envíe la cookie `Secure`. Configurar `SECRET_KEY`
desde el entorno del proceso con al menos 32 bytes UTF-8 aleatorios; si falta,
los endpoints IAM fallan cerrados. La aplicación no carga `.env` automáticamente.
La autenticación no utiliza la sesión firmada predeterminada de Flask.
Las rutas IAM rechazan HTTP cuando `Secure` está habilitado; si se termina TLS
en un proxy, el servidor WSGI debe recibir de forma confiable el esquema HTTPS.

El cliente solicita `GET /api/v1/auth/csrf`, conserva su cookie y envía el token
en `X-CSRF-Token` para `POST /api/v1/auth/login`. Tras el login usa la cookie
rotada y el nuevo token devuelto en la cabecera. `POST /api/v1/auth/logout`
requiere CSRF y revoca solo esa sesión. `GET /api/v1/auth/me` consulta estado y
rol actuales: una cuenta inactiva deja de estar autorizada. El guard de roles
puede reutilizarse en futuros endpoints; las reglas administrativas permanecen
en los casos de uso. La desactivación y el restablecimiento administrativo de
contraseña revocan todas las sesiones de esa cuenta en su misma transacción;
una reactivación posterior no restaura sesiones antiguas. La sesión vence tras
30 minutos de inactividad o a las
ocho horas desde su creación. Login admite diez intentos por IP en cinco minutos
**por proceso**; esta defensa inicial no es un límite compartido entre procesos.

La suite unitaria completa aprobó 135 pruebas en el entorno virtual del backend
tras incorporar la administración HTTP.
Las pruebas unitarias HTTP usan SQLite efímero. Las pruebas MySQL de sesiones
permanecen separadas y omitidas por defecto. Exigen `0003_sesiones_iam` en
`recon_tests`, además de las barreras existentes de destino y aislamiento. No
aplican migraciones ni limpian tablas. El responsable confirmó la aplicación
de `0003` en ambas bases y las 22 pruebas de integración en `recon_tests`.
También ejecutó el flujo HTTP con Flask `test_client()` y el SUPERADMIN
existente en `recon_dev`: login, sesión activa, logout, revocación y rechazo
posterior funcionaron; la Persona `id_persona=1`, la cuenta y su auditoría
permanecieron conservadas y no quedaron sesiones nuevas activas. Esta prueba
manual ejerció MySQL real, pero no sustituye las pruebas unitarias ni las de
integración. La política de limpieza de sesiones expiradas sigue pendiente.
Ninguna tabla se crea al arrancar Flask.

## Administración HTTP de cuentas — incremento del prototipo

El contrato de [`openapi.json`](./openapi.json) incluye `GET /api/v1/iam/roles`,
`GET /api/v1/iam/usuarios`, `GET /api/v1/iam/usuarios/{usuario_id}`,
`POST /api/v1/iam/usuarios` y `PATCH` sobre las subrutas `/rol` y `/estado`.
Todas exigen una sesión SUPERADMIN activa. Las escrituras exigen además el
`X-CSRF-Token` asociado a la cookie actual. El listado usa `limite` (1 a 100,
predeterminado 50) y `desplazamiento` (0 a 1 000 000); las respuestas de cuentas
solo contienen identificador, login, rol y estado. No incluyen hash, contraseña,
sesiones ni auditoría.

La creación permite únicamente ADMINISTRADOR y OPERADOR. Los cambios de rol y
estado respetan la protección del SUPERADMIN inicial y reutilizan los casos de
uso que auditan las operaciones. Desactivar una cuenta revoca sus sesiones. El
cambio de login y el restablecimiento de contraseña no tienen rutas HTTP en
este incremento. La validación de estas rutas con MySQL real queda pendiente;
las pruebas HTTP de este incremento usan SQLite efímero.

## Procedimiento histórico de solo lectura previo a `0002_identity_iam`

Desde `backend/`, en una misma terminal PowerShell, ejecutar el verificador
antes de solicitar la migración. La contraseña se introduce con entrada oculta
y permanece únicamente en el entorno del proceso. `DB_NAME` se usa para impedir
que desarrollo y pruebas compartan nombre; el script solo conecta a
`recon_tests` con `recon_test_app`.

```powershell
try {
    $env:DB_HOST = '127.0.0.1'
    $env:DB_PORT = '3306'
    $env:DB_NAME = 'recon_dev'
    $env:DB_TEST_NAME = 'recon_tests'
    $env:DB_TEST_USER = 'recon_test_app'
    $clavePruebas = Read-Host 'Contraseña de recon_test_app' -AsSecureString
    $env:DB_TEST_PASSWORD = [System.Net.NetworkCredential]::new('', $clavePruebas).Password
    Remove-Variable clavePruebas
    & '.\.venv\Scripts\python.exe' -B scripts\verificar_recon_tests.py
} finally {
    'DB_HOST','DB_PORT','DB_NAME','DB_TEST_NAME','DB_TEST_USER','DB_TEST_PASSWORD' |
        ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
    Remove-Variable clavePruebas -ErrorAction SilentlyContinue
}
```

El verificador termina con `APTO` solo si la conexión real corresponde al
destino de pruebas, Alembic está exactamente en `0001_personas`, las tablas de
Personas están presentes en InnoDB y no existe ninguna tabla IAM. Su salida no
incluye credenciales ni cadenas de conexión. No carga archivos `.env`, no aplica
migraciones y no modifica datos. Un resultado `NO APTO` detiene el proceso y
requiere revisar la discrepancia antes de continuar.

## Sesiones anónimas y limpieza pendiente

Las sesiones anónimas de `/api/v1/auth/csrf` vencen tras 30 minutos de
inactividad o a las ocho horas de su creación. Una sesión vencida se rechaza
aunque la fila permanezca almacenada. Antes de operar el servicio de forma
sostenida se debe aprobar una limpieza periódica, en lotes acotados, limitada
a sesiones expiradas o revocadas. No hay tarea automática ni borrados globales.
La frecuencia y la retención definitivas están pendientes de consolidación.

## Validación manual de 0003 en recon_tests (realizada)

Desde Git Bash, el procedimiento preparado comprueba el destino real
`127.0.0.1:3306/recon_tests` con `recon_test_app`, exige exactamente la revisión
`0002_identity_iam`, verifica tablas, FK, UNIQUE, CHECK y roles previos, y exige
la ausencia de `sesion_usuario`. Solicita la contraseña de forma oculta, genera
un respaldo completo con `mysqldump` en `~/ReconFacialBackups` fuera del
repositorio, repite la comprobación previa y ejecuta **solo**
`db upgrade 0003_sesiones_iam` con `create_app(pruebas=True)`. Después comprueba
revisión, estructura y ausencia de registros de sesión. Cualquier fallo detiene
el proceso sin reintentos ni limpiezas destructivas. El responsable ya ejecutó
y validó la migración; estos comandos documentan el procedimiento utilizado y
no deben repetirse sin una nueva revisión del estado real.

```bash
cd /c/Users/casa/Desarrollo/recon_platform/backend
bash scripts/aplicar_0003_recon_tests.sh
```

El responsable ejecutó las 22 pruebas de la carpeta de integración mediante el
script separado. Este pide
la contraseña de forma oculta, comprueba el esquema antes y después y exige que
no queden Personas, cuentas, auditorías ni sesiones de prueba. Las pruebas usan
transacciones externas revertibles y no ejecutan migraciones.

```bash
cd /c/Users/casa/Desarrollo/recon_platform/backend
bash scripts/probar_0003_recon_tests.sh
```

Ambos scripts eliminan sus variables temporales al finalizar. La salida `APTO`
del verificador y el resumen de pytest son aptos para revisión. No compartir
el respaldo ni información privada de tablas.

## Aplicación manual de 0003 en recon_dev (realizada)

`recon_dev` está en `0003_sesiones_iam` y conserva una Persona ficticia con
`id_persona=1`, un SUPERADMIN activo y su auditoría de bootstrap, según la
validación manual reportada por el responsable. El procedimiento de Git Bash
ya fue ejecutado satisfactoriamente. Solicita la contraseña de `recon_dev_app` con
entrada oculta y no utiliza las credenciales de pruebas. La aplicación recibe
solo `DB_NAME=recon_dev`, `DB_USER=recon_dev_app` y
`create_app(pruebas=False)`; se desactiva la carga automática de `.env`.

Antes de respaldar y otra vez inmediatamente antes de migrar, el verificador
consulta la identidad real `127.0.0.1:3306/recon_dev` con `recon_dev_app` y
exige la revisión exacta `0002_identity_iam`. Comprueba tablas InnoDB,
restricciones anteriores, roles, ausencia de `sesion_usuario`, Persona
`id_persona=1`, la única cuenta SUPERADMIN activa y su única auditoría de
bootstrap. El respaldo completo queda en `~/ReconFacialBackups`, fuera del
repositorio, dentro de una carpeta con herencia ACL de Windows desactivada y
acceso concedido a la cuenta Windows que ejecuta el script. Se comprueban
marcadores de esquema, filas existentes y finalización de `mysqldump`.

Tras aplicar exclusivamente `0003_sesiones_iam`, el mismo verificador comprueba
la nueva tabla, PK, FK, índice, tipos y nulabilidad; exige la preservación de
Persona, SUPERADMIN y auditoría. Cualquier discrepancia detiene el procedimiento
sin reintentos, reversión automática, limpieza de tablas ni bootstrap. El
siguiente comando queda como referencia del procedimiento ya ejecutado; no
repetirlo sin una nueva revisión del estado real:

```bash
cd /c/Users/casa/Desarrollo/recon_platform/backend
bash scripts/aplicar_0003_recon_dev.sh
```

La salida `APTO` y el resumen final pueden compartirse sin la contraseña, el
hash ni datos personales. El respaldo contiene datos privados y no debe
versionarse ni compartirse. Si el respaldo o la verificación posterior fallan,
detenerse y revisar el estado antes de intentar cualquier operación adicional.

## Prueba HTTP manual del SUPERADMIN en recon_dev (realizada)

Después de aplicar y validar `0003_sesiones_iam` en `recon_dev`, el procedimiento
preparado comprueba con consultas de solo lectura la identidad real
`127.0.0.1:3306/recon_dev` con `recon_dev_app`, la revisión exacta `0003`,
las tablas y restricciones de Personas e IAM, la Persona `id_persona=1`, el único
SUPERADMIN activo y su auditoría de bootstrap. A diferencia del verificador
inmediato de migración, acepta filas de sesión ya revocadas o expiradas.

El script de Git Bash pide oculta la contraseña de MySQL. Luego el script Python
pide también con entrada oculta el login y la contraseña del SUPERADMIN, sin
argumentos ni archivos para estas credenciales. Genera una `SECRET_KEY`
temporal aleatoria para este proceso y usa la excepción HTTP local ya aprobada.
Con una instancia nueva de Flask `test_client()` comprueba: `GET /auth/me` sin
sesión → 401; obtención de CSRF; login → 200 y rotación de cookie/CSRF;
`GET /auth/me` → identidad SUPERADMIN; logout → 200; nuevo `GET /auth/me` → 401.
No imprime login, contraseña, cookies, tokens, digest ni hash. En el cierre
revoca únicamente las sesiones identificadas como creadas por este flujo y
verifica que ninguna sesión activa nueva permanezca. No borra filas; pueden
quedar sesiones revocadas o expiradas. Si una falla de infraestructura impide
confirmar la revocación, informa `NO APTO` y exige revisión manual antes de
repetir el procedimiento.

El responsable informó una ejecución satisfactoria del siguiente procedimiento.
No repetirlo sin nueva autorización, pues crea y revoca sesiones en `recon_dev`:

```bash
cd /c/Users/casa/Desarrollo/recon_platform/backend
bash scripts/probar_http_superadmin_recon_dev.sh
```

`test_client()` ejerce las rutas Flask, el manejo de cookies/CSRF, los casos de
uso y la persistencia MySQL real, sin abrir un puerto HTTP público. No prueba
el comportamiento de un navegador real, la entrega de cookies `Secure` por
HTTPS, la terminación TLS, una configuración de proxy ni el frontend React;
eso requiere una validación posterior en un entorno HTTP/HTTPS controlado.

## Incremento 0006 — EventoAcceso manual (implementación preparada)

El código de 0006 incorpora `EventoAcceso` en Accesos, con registro humano
`ENTRADA`/`SALIDA`, jornada civil `America/Bogota`, incidencia nullable y
auditoría en una misma transacción. La secuencia toma únicamente el último
`AUTORIZADO` de la Persona en la jornada; `RECHAZADO` no la modifica. El modelo
reserva `FACIAL` y una FK nullable hacia `DispositivoEdge`, pero la API nueva
solo produce eventos `MANUAL`, con `id_dispositivo=NULL`. No se implementaron
observaciones biométricas, un adaptador HTTP Edge ni acciones físicas.

La migración candidata está en
[`migrations/versions/0006_evento_acceso.py`](./migrations/versions/0006_evento_acceso.py).
**No está aplicada** por esta entrega. Crea solamente `evento_acceso` y exige
InnoDB, FK restrictivas, valores CHECK, `UNIQUE` de clave idempotente e índices
para jornada y consultas. La hora se guarda en UTC `DATETIME(6)`; `tzdata` es
dependencia explícita para obtener la zona IANA también en Windows.

### API web humana

El contrato versionado se encuentra en [`openapi.json`](./openapi.json). Todas
las rutas nuevas usan sesión humana, autorización backend y `Cache-Control:
no-store`; `POST` exige además `X-CSRF-Token` e `Idempotency-Key` UUIDv4
canónico:

| Ruta | Función |
|---|---|
| `GET /api/v1/eventos-acceso/personas-elegibles` | Búsqueda acotada de Persona activa por documento, identificador institucional o prefijo de nombre; devuelve PK, nombre y final del documento. No concede permisos administrativos de Personas. |
| `POST /api/v1/eventos-acceso/manual` | Registra una declaración nueva (`201`) o devuelve el mismo evento para un reintento idéntico (`200`, `Idempotent-Replay: true`). Clave reutilizada para otro actor o contenido: `409`. |
| `GET /api/v1/eventos-acceso/historial` | OPERADOR: filas solo de hoy Bogotá con movimiento, resultado y hora redondeada a la hora; sin PK, Punto, Persona, actor ni incidencia por fila. Administradores: histórico ampliado con filtros y paginación. |
| `GET /api/v1/eventos-acceso/alertas` | OPERADOR: conteos por tipo de incidencia de hoy, sin identificadores ni hora. Administradores: incidencias ampliadas paginadas. |
| `GET /api/v1/eventos-acceso/incidencias/{id_evento}` | Detalle personal solo para ADMINISTRADOR/SUPERADMIN. |

Para OPERADOR, los filtros de identidad, fechas y Punto se rechazan; ninguna
ruta de detalle personal le permite recuperar un ID. La hora aproximada de su
historial conserva utilidad operacional, pero puede existir correlación por
observación externa cuando el volumen es bajo: esta proyección no promete
anonimato absoluto. La política general de retención y privacidad sigue
PENDIENTE. Las alertas de 0006 son datos consultables, sin push ni frontend.

El caso de uso descarta la transacción de lectura que pudo abrir el guard IAM,
bloquea la fila de Persona y abre después la primera lectura consistente de
eventos. Todos los escritores futuros para esa Persona deben respetar el
mismo bloqueo; la prueba MySQL preparada fuerza una snapshot previa para
comprobar que el caso de uso la descarta. La
restricción `UNIQUE` evita dobles inserciones de la misma clave. Un reintento
del mismo actor y declaración devuelve el resultado original aunque Persona o
Punto estén ahora inactivos; una declaración nueva exige estados activos.
Evento y auditoría de éxito se confirman juntos o se revierten juntos.

### Validación controlada pendiente

[`scripts/verificar_recon_0006.py`](./scripts/verificar_recon_0006.py) verifica
identidad, revisión, objetos, restricciones y huellas de datos previos. Los
scripts [`aplicar_0006_recon_tests.sh`](./scripts/aplicar_0006_recon_tests.sh)
y [`aplicar_0006_recon_dev.sh`](./scripts/aplicar_0006_recon_dev.sh) están
preparados para revisión independiente: exigen autorización explícita,
preflight, comprobación administrativa de objetos, respaldo privado completo,
confirmación literal y postflight. El script
[`probar_0006_recon_tests.sh`](./scripts/probar_0006_recon_tests.sh) queda
reservado para pruebas MySQL reales autorizadas. Las pruebas de concurrencia
usan dos conexiones independientes y limpian solo filas ficticias creadas
por su fixture. No se debe ejecutar ninguno de estos procedimientos antes de
revisar el código y autorizar la operación correspondiente; primero
`recon_tests`, después `recon_dev`, sin reintentos ni restauraciones automáticas.
