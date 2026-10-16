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
migración `0002_identity_iam` está preparada y **no aplicada**. No existen aún
endpoints IAM, sesiones HTTP ni registro público de cuentas.

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

## Identity/IAM: bootstrap pendiente de ejecución

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

Tras autorización, revisar y aplicar manualmente `0002_identity_iam` en cada
base prevista y verificar su esquema. La migración crea roles y tablas, pero
ninguna cuenta ni contraseña. Para provisionar el primer SUPERADMIN en una base
ya migrada, cargar sus variables de conexión en el entorno del proceso y
ejecutar explícitamente desde `backend/`:

```powershell
& '.\.venv\Scripts\python.exe' -B -m flask --app recon_platform:create_app bootstrap-superadmin
```

El comando exige confirmar el destino previsto y solicita login y contraseña
con entrada oculta y confirmación; no acepta la contraseña como argumento. Si
ya existe una cuenta SUPERADMIN, no
crea otra. No se ejecuta al importar ni al iniciar Flask. Comprobar el destino
de la conexión antes de invocarlo; este incremento no ejecutó el comando.

## Integración MySQL preparada, pendiente de ejecución

Pytest descubre únicamente `tests/unit` por defecto. Las pruebas en
`tests/integration` requieren además `RECON_RUN_MYSQL_INTEGRATION=1`; sin esa
variable se omiten incluso si se selecciona la carpeta expresamente. La
aplicación no carga `.env` automáticamente: quien ejecute las pruebas debe
proporcionar las variables al proceso sin imprimir las contraseñas.

Antes de cada conexión de prueba se exige `mysql+pymysql` hacia
`127.0.0.1:3306`, base `recon_tests` y usuario `recon_test_app`. Se consulta
también la identidad real de la conexión, una revisión conocida de Alembic
(`0001_personas` o `0002_identity_iam`) y el motor InnoDB de las tablas
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

El responsable verificó previamente las pruebas de Personas sobre MySQL. Las
pruebas de IAM contra la migración `0002_identity_iam` están preparadas, pero
siguen sin ejecutarse. Exigen además esa revisión exacta antes de escribir y
comprueban esquema, roles, ausencia inicial de cuentas, FK, unicidades, casos
de uso y rollback. La comprobación de ausencia de cuentas debe ejecutarse
después de aplicar `0002` y antes del bootstrap operativo. Las cuentas
ficticias de las otras pruebas, incluida la SUPERADMIN de prueba, se crean
dentro de transacciones revertibles; no se invoca el comando de bootstrap.

Tras autorizar la migración y verificar su resultado, se pueden seleccionar
solo las pruebas IAM con el mismo entorno y la misma activación explícita:

```powershell
$env:RECON_RUN_MYSQL_INTEGRATION = "1"
& '.\.venv\Scripts\python.exe' -B -m pytest -p no:cacheprovider tests/integration/test_identidad_mysql.py
Remove-Item Env:RECON_RUN_MYSQL_INTEGRATION
```

Las pruebas unitarias no sustituyen esta validación MySQL.

## Comprobación manual de solo lectura antes de `0002_identity_iam`

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
