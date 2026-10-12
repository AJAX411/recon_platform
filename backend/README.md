# Backend — Proyecto Recon Facial

Backend de la plataforma web del Proyecto Recon Facial.

## Alcance implementado

La fábrica Flask conserva la ruta temporal `/_diagnostico`. El módulo Personas
dispone de entidades de dominio, casos de uso internos `RegistrarPersona` y
`ConsultarPersona`, repositorios SQLAlchemy y una migración inicial **preparada,
no aplicada**. No hay endpoints de Personas, autorización web, enrolamiento facial
ni conexión MySQL validada en este incremento. El registro interno es una parte
de CU-03/HU-04; no completa esos casos de uso.

Organización provisional: API/presentación → aplicación/casos de uso →
dominio/reglas → infraestructura/persistencia. El dominio no importa el ORM.

## Entorno

El desarrollo utiliza un entorno virtual local ubicado en:

`.venv/`

Las credenciales y secretos reales deben almacenarse en `.env`,
archivo que no debe versionarse.

`.env.example` sirve únicamente como plantilla segura de configuración. La
aplicación lee variables del entorno del proceso; no carga `.env` automáticamente.

Para persistencia, configurar `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y
`DB_PASSWORD`. `DB_TEST_NAME` designa un esquema de pruebas distinto de
`DB_NAME`; si la configuración de pruebas apunta al mismo nombre, la aplicación
falla antes de abrir conexión. Se usa `utf8mb4`. Si no se definen las variables
de base de datos, la fábrica permite solamente la ruta diagnóstica. Si se
definen parcialmente, falla con un error sin revelar la contraseña.

Las unidades de trabajo confirman o revierten la operación completa; los
repositorios no hacen commits. Los modelos guardan `DATETIME` en UTC por
convención y devuelven fechas con zona UTC al dominio. Las restricciones de
unicidad y la FK también se declaran en la migración para proteger concurrencia
e integridad referencial. El catálogo inicial de seis TipoPersona se carga allí.

Las pruebas unitarias se ejecutan desde `backend/` con el entorno virtual
existente: `python -B -m pytest -p no:cacheprovider tests/unit`. Estas pruebas
no abren MySQL. La migración y las pruebas de integración sobre un esquema
MySQL exclusivo de test quedan pendientes de autorización y ejecución posterior.
