# Backend — Proyecto Recon Facial

Backend de la plataforma web del Proyecto Recon Facial.

## Alcance implementado

La fábrica Flask conserva la ruta temporal `/_diagnostico`. El módulo Personas
dispone de entidades de dominio, casos de uso internos `RegistrarPersona` y
`ConsultarPersona` y repositorios SQLAlchemy. La migración `0001_personas` fue
aplicada y verificada manualmente en `recon_tests` y `recon_dev`; el responsable
informó 10 pruebas de integración MySQL aprobadas y persistencia comprobada en
desarrollo. Son resultados históricos, no una ejecución de este incremento.
El registro interno es una parte de CU-03/HU-04; no completa esos casos de uso.
No hay endpoints de Personas ni enrolamiento facial.

Identity/IAM incorpora Rol, UsuarioPlataforma independiente de Persona, casos
de uso administrativos exclusivos de SUPERADMIN, verificación de credenciales,
auditoría de operaciones exitosas y un comando explícito de bootstrap. La
migración `0002_identity_iam` fue aplicada y verificada en ambas bases por el
responsable. La primera cuenta SUPERADMIN existe en desarrollo. El incremento
actual añade endpoints de autenticación HTTP, sin registro público ni endpoints
de administración de cuentas. `0003_sesiones_iam` fue aplicada y validada en
`recon_tests` y `recon_dev`, según las ejecuciones reportadas por el responsable.

Organización provisional: API/presentación → aplicación/casos de uso →
dominio/reglas → infraestructura/persistencia. El dominio no importa el ORM.

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
(`0001_personas`, `0002_identity_iam` o `0003_sesiones_iam`) y el motor InnoDB de las tablas
correspondientes. Cualquier fallo detiene la
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
