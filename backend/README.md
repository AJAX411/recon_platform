# Backend — Proyecto Recon Facial

Backend de la plataforma web del Proyecto Recon Facial.

## Alcance implementado

La fábrica Flask conserva la ruta temporal `/_diagnostico`. El módulo Personas
dispone de entidades de dominio, casos de uso internos `RegistrarPersona` y
`ConsultarPersona`, repositorios SQLAlchemy y una migración inicial **preparada,
no aplicada**. No hay endpoints de Personas, autorización web, enrolamiento facial
ni esquema MySQL validado mediante migraciones en este incremento. El registro
interno es una parte de CU-03/HU-04; no completa esos casos de uso.

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
no abren MySQL. La migración inicial sigue sin aplicarse.

## Integración MySQL preparada, pendiente de ejecución

Pytest descubre únicamente `tests/unit` por defecto. Las pruebas en
`tests/integration` requieren además `RECON_RUN_MYSQL_INTEGRATION=1`; sin esa
variable se omiten incluso si se selecciona la carpeta expresamente. La
aplicación no carga `.env` automáticamente: quien ejecute las pruebas debe
proporcionar las variables al proceso sin imprimir las contraseñas.

Antes de cada conexión de prueba se exige `mysql+pymysql` hacia
`127.0.0.1:3306`, base `recon_tests` y usuario `recon_test_app`. Se consulta
también la identidad real de la conexión, la revisión `0001_personas` de
Alembic y el motor InnoDB de las tres tablas. Cualquier fallo detiene la
ejecución antes de las escrituras. Las pruebas no crean ni migran tablas y no
usan `create_all`, `drop_all` ni borrados globales. Cada prueba de datos se
ejecuta en una transacción externa que se revierte al terminar; los commits de
los casos de uso quedan dentro de savepoints. No se eliminan registros ajenos.

Tras aprobar la ejecución, comprobar el destino y el estado vacío de
`recon_tests`, revisar y aplicar allí manualmente la migración `0001_personas`,
y confirmar el esquema. Con `DB_NAME`, `DB_TEST_NAME`, `DB_TEST_USER` y
`DB_TEST_PASSWORD` configurados en el entorno del proceso, además de
`DB_HOST=127.0.0.1` y `DB_PORT=3306`, ejecutar desde `backend/`:

```powershell
$env:RECON_RUN_MYSQL_INTEGRATION = "1"
& '.\.venv\Scripts\python.exe' -B -m pytest -p no:cacheprovider tests/integration
Remove-Item Env:RECON_RUN_MYSQL_INTEGRATION
```

La ejecución real y el comportamiento de los savepoints en este servidor
siguen pendientes de comprobación; no se consideran resultados aprobados por
el mero hecho de tener las pruebas preparadas.
