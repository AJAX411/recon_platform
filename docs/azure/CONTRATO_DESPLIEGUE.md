# VIGENTE — Contrato para transferir Recon Facial a Azure

Macroencargo F, 20/11/2026. **Candidata D/E/F con reservas; Incremento0010
ABIERTO. Azure NO desplegado ni validado por esta sesión.** La versión de código
es el commit que contiene este estado; contrastar `git rev-parse HEAD` con el SHA
remoto de main y con `TRASPASO_AZURE_POST_GIT.md`, generado externamente después
del push verificado. No insertar una huella autorreferente en el propio commit.
El SHA `affa5e5064e8eeb014840af962bf3e88e21c5202` queda como corte histórico
Macro C, anterior a D/E/F. El acta externa indicará PUBLICADO o NO PUBLICADO;
este contrato no sustituye esa comprobación.

## Código y artefactos canónicos

Monorepo privado `AJAX411/recon_platform`, rama `main`. Frontend en
[frontend/src](../../frontend/src/), SPA HTML5/CSS/JavaScript Vanilla con Bootstrap
5.3.8. Vite 7.3.8 solo desarrollo/build; Vitest 3.2.7 herramienta de pruebas.
Node no se ejecuta en el runtime publicado. React y candidata se conservan
localmente, ignorados y ausentes de un clon de despliegue.

Backend Python 3.14.x/Flask 3.1.3/SQLAlchemy 2.0.54, Flask-SQLAlchemy 3.1.1,
Flask-Migrate 4.1.0/Alembic 1.20.0/PyMySQL[rsa] 1.2.2, según
[pyproject](../../backend/pyproject.toml). Versiones transitivas y Gunicorn 25.3.0
están en [runtime](../../backend/deploy/requirements-runtime.txt) y
[WSGI](../../backend/deploy/requirements-wsgi.txt). No sustituir por el dominio
del ejemplo del profesor ni añadir reconocimiento facial/hardware.

## Bases verificadas linux/amd64

| Base | Referencia fijada en Dockerfile/Compose |
|---|---|
| Python 3.14.10 | `python:3.14.10-slim-bookworm@sha256:1faf2343e747208b2a36e5f2b5ff908ec3b2d0078a6a7bfe73b535698fe83909` |
| Node 26.13.1 | `node:26.13.1-bookworm-slim@sha256:18a166e2d50578afe933434857ed2d9059bd1aa398a223e9c89eb4302354f079` |
| Nginx 1.30.7 | `nginx:1.30.7-alpine@sha256:4d1d4ce08432dc7dfe4af762cb224ce6b5273ae878f41e020ea2425d02ea91a4` |
| MySQL LTS 8.4 | `mysql:8.4@sha256:24989179f58856db763f418010c1169fecc944e3ec1ea7e921572d83eb070f70` |

MySQL declara 8.4.11-1.el9 en metadatos de la imagen local. Las referencias están
en [backend Dockerfile](../../backend/Dockerfile),
[frontend Dockerfile](../../frontend/Dockerfile) y [Compose](../../compose.yaml).
Contexto de ambos builds: raíz del repo, con whitelists dockerignore específicas;
sin .venv/node_modules/dist Windows, respaldos, secretos ni datos SQL.

Build frontend: npm ci --ignore-scripts --no-audit --no-fund, npm run build.
Nginx recibe dist; no dev servers ni Node/npm/node_modules. Backend instala
solo wheels de dependencias dentro de Linux, sin instalar aplicación en Windows.
No hay imágenes construidas publicadas en registro remoto ni push de imágenes.
Digests/IDs del motor local no certifican disponibilidad de un registry cloud.
Pip está fijado por versión, sin lock binario integral --require-hashes. El
inventario de módulos puede variar en orden, aunque su conjunto y código coincidan.

## Arranque, API, autenticación y liveness

Factory de producto: `recon_platform:create_app(pruebas=False)`;
WSGI: `app_wsgi:create_wsgi_app()`; CLI contenedor: `app_wsgi:create_cli_app`.
Gunicorn usa sync, dos workers, bind0.0.0.0:8000, timeout30, sin access log y
forwarded-allow-ips vacío: el [adaptador](../../backend/deploy/app_wsgi.py) valida
el peer frontend y X-Forwarded-Proto=https. No confía en headers reenviados del
cliente. Flask DEBUG=False. No ejecutar flask run público ni RECON_LOCAL_HTTP.

[OpenAPI](../../backend/openapi.json): base `/api/v1`,36 operaciones, incluido PATCH IAM/login. Sesiones
humanas stateful con cookie opaca `recon_session`, Path=/api/v1, HttpOnly,
Secure, SameSite=Lax; CSRF en escrituras. GET /api/v1/auth/csrf prepara sesión;
POST login devuelve el token CSRF renovado en X-CSRF-Token; no guardarlo en logs.
El backend autoriza roles, los guards UI solo ayudan a navegar. Sin JWT humano
en localStorage, registro público ni relación automática Persona-cuenta.

`GET /_diagnostico` es **liveness de factory/proceso**, no readiness de MySQL,
esquema, login o datos. Nginx tiene liveness interno8080, no publicarlo. MySQL
mysqladmin ping puede responder aunque falte autenticación. Antes de declarar
salud de despliegue comprobar DB/revisión/catálogos y login HTTPS reales.

## Variables y secretos — por nombre

Configuración pública del backend contenedor: DB_HOST, DB_PORT, DB_NAME, DB_USER,
RECON_SESSION_COOKIE_SECURE. Lecturas privadas: DB_PASSWORD_FILE, SECRET_KEY_FILE.
La factory del adaptador carga DB_PASSWORD/SECRET_KEY solo en memoria desde
archivos bajo /run/secrets; no valores baked en imagen, CLI, Git o logs.

Variables Compose: RECON_DB_ROOT_PASSWORD_FILE, RECON_DB_APP_PASSWORD_FILE,
RECON_SESSION_KEY_FILE, RECON_TLS_CERT_FILE, RECON_TLS_KEY_FILE,
RECON_PYTHON_IMAGE, RECON_NODE_IMAGE, RECON_NGINX_IMAGE, RECON_MYSQL_IMAGE,
RECON_BACKEND_IMAGE, RECON_FRONTEND_IMAGE, RECON_HTTPS_PORT.
[Plantilla sin secretos](../../deploy/container.env.example).
Credenciales root/app, sesiones, demo y TLS de Azure deben ser NUEVAS, con permisos
restrictivos. No copiar archivos privados del laboratorio Windows ni del informe
de infraestructura. La Deploy Key Ubuntu es solo lectura y no se usa para push.

El adaptador actual exige **DB_HOST=db, DB_PORT=3306, DB_NAME=recon_container_0010,
DB_USER=recon_container_app y cookie Secure**. Azure puede usar esos nombres
lógicos en un volumen/base nuevos y aislados con credenciales nuevas; no renombrar
silenciosamente ni apuntar a MySQL administrado externo. Otro destino necesita
adaptación de código revisada y regresión, no un env improvisado.

## Topología local comprobada y diferencia Azure

| Servicio | Red y exposición local |
|---|---|
| frontend | Nginx sin root, HTTPS8443; solo127.0.0.1:8443 publicado |
| backend | USER10001,8000 interno, web/data internas, sin puerto host |
| db |3306/33060 internos, data interna, volumen nuevo mysql_isolated |

Backend/frontend: read-only, tmpfs/tmp, cap_dropALL y no-new-privileges.
Frontend añade entrada_local bridge con binding loopback y masqueradefalse para
Docker Desktop; no constituye una política de egress cloud ya auditada.

**Bloqueo público pendiente:** [Nginx actual](../../frontend/nginx.conf) permite
solo localhost/127.0.0.1 y monta TLS de laboratorio. Para
`recon-platform-g01.northcentralus.cloudapp.azure.com` se necesita una configuración
Azure revisada: server_name y regla de Host exactos, certificado válido del FQDN,
entrada443 hacia8443 o terminación TLS/proxy acotado compatible con cookies.
No basta abrir NSG o mapear otro puerto; no bajar Secure ni aceptar cualquier
X-Forwarded-Proto. Puerto80 solo si se implementa/autorizan ACME o redirect;
**no publicar8080 de liveness como HTTP del sitio**. DB/API/socket Docker nunca
públicos. La variante separada [deploy/azure](../../deploy/azure/README.md) está
PREPARADA / NO DESPLEGADA: FQDN exacto validado, TLS externo, perfil exclusivo,
bind loopback por defecto y límites iniciales de recursos. Compose config y
nginx-t con fixtures sintéticos aprobaron; no se verificaron DNS/NSG/TLS público,
permisos POSIX de secretos o rendimiento en la VM. Docker local probado NO equivale
a Docker público listo en Azure. Para publicar443 se requiere permiso cloud y
verificación de bind/NSG/firewall, sin exponer API/DB.

## Esquema, CLI y datos ficticios: puerta independiente

[Seis revisiones](../../backend/migrations/versions/)0001→0006, final
0006_evento_acceso,12 tablas (11 ORM más alembic_version),3 roles,6 tiposPersona.
El arranque normal nunca migra ni hace bootstrap. Revisar env Alembic: su cuerpo
ejecuta migración cuando se invoca; no importarlo como validación inerte.

Antes del primer DDL Azure: identidad de servidor/base/usuario/volumen nuevos,
permisos, esquema vacío, compatibilidad y respaldo cuando haya datos. Bajo la
factory CLI *_FILE ya validada, dentro del servicio autorizado:

```text
flask --app app_wsgi:create_cli_app db upgrade --directory /opt/recon/migrations
flask --app app_wsgi:create_cli_app bootstrap-superadmin
```

Son operaciones sujetas a permiso para CADA destino. El ensayo E ejecutó las
seis revisiones y bootstrap mediante CLI oficial (test_cli_runner dentro del
contenedor propio), solo después de comprobar identidad/usuario/volumen nuevos y
esquema vacío. No repetir en un volumen con datos; Azure necesita su propia puerta. Bootstrap pide datos ocultos, protege la SUPERADMIN única e idempotente;
no pasar contraseñas en args ni crear cuentas por SQL manual. ADMINISTRADOR y
OPERADOR se crean por la administración oficial con auditoría. Usar solo fixtures
ficticios; no declarar biometría, apertura física ni supresión Persona implementada.

## Evidencia, reservas y recuperación

Ensayo E nuevo, post-D/E: 80 comprobaciones HTTPS/API reales y
26 de Edge real contra Nginx/Gunicorn/MySQL; no API ficticia.
PATCH/login probado con normalización,409,400,403, sesión/credencial conservadas,
auditoría y rollback MySQL en proceso auxiliar sin alterar producto. Una Persona,
un Punto, un Edge administrativo inactivo, tres cuentas y tres eventos ficticios.
Parada DB→503 genérico y reinicio completo conservaron conteos/huellas públicas
y revisión0006; login modificado verificado tras reinicio. Servicios propios
apagados sin-v, volumen nuevo y volúmenes previos conservados.

Se comprobaron fuentes de las imágenes actuales por SHA:81 módulos backend y
artefactos frontend recompilados. Construcción offline equivalente: dependencias
backend de imagen local verificada y COPY de TODAS las fuentes actuales; Nginx
limpio recibe el build frontend actual. No hubo pip/npm install ni descargas de
capas; el primer auxiliar usó un FROM con ID mal expresado, consultó metadatos de
registry y falló; después se corrigió a etiqueta local verificada. No se afirma
una reconstrucción fría desde cero de los Dockerfiles con instalación nueva.

Nuevas pruebas acotadas:68 backend,12 frontend,4 renderizador Azure, Ruff/ESLint
y build PASS. AST Python sin docstrings y cuerpo JS tras encabezado idénticos;
202 frontend y361+1 backend del corte D se reutilizan por semántica, no se presentan
como suite global nueva. Histórico anterior:190/20/87/37, otro ensayo y volumen.
[Detalle local](../pruebas/DOCKER_LOCAL_0010.md), [guía](../../deploy/README.md).
Audit producción sin avisos al corte;3 paquetes dev afectados, aislados fuera del
runtime. No declarar cero vulnerabilidades globales ni vigencia indefinida del audit.
G6 Windows1045, C15/D08/D09/D13, D12 humana y zoom nativo200% siguen pendientes.
Al apagar E no quedaron sesiones autenticadas activas; las filas anónimas o
revocadas no se limpiaron por SQL. Credenciales/clave/TLS locales nuevos se
conservan privados fuera del repo/ZIP. La política de limpieza/retención sigue
pendiente; no transferir secretos del ensayo a Azure.

Rollback de código: conservar revisión anterior y artefactos, sin reset/force ni
sobrescribir trabajo. DB: persistencia no equivale a backup; antes de cualquier
actualización cloud con datos, backup privado completo y restauración verificada.
No downgrade ni eliminar volumen por conveniencia. Down del proyecto propio
sin-v conserva datos; no prune. No restaurar un volumen de laboratorio sobre otro
destino ni reutilizar cuentas/secretos Windows.

## Coordinación Azure y versión publicada

[Checklist paso19 y20–23](./CHECKLIST_DESPLIEGUE.md). Según el informe de
infraestructura20/11: Ubuntu24.04.5, Docker29.10.0/Compose5.8.0 y Deploy Key lectura
preparados; todavía sin clon. No verificado en vivo desde Macro C. Sitio propuesto
/home/azureuser/recon-platform/source, condicionado a inspección previa.
El encargo F autoriza Git de forma independiente solo tras F2 APTO y remoto
sincronizado. El acta externa acredita el SHA realmente publicado y el estado
de push; usar ese SHA congelado para el clon, nunca el corte Macro C como D/E/F
ni git pull indiscriminado al grabar.
Git publicado no acredita DNS/HTTPS público, recursos cloud, costos o ejecución
de automatizaciones. No se accede a Azure desde este encargo.

---

## Delta humano posterior a E — Bienvenido

La fuente viva del login conserva el título izquierdo **Bienvenido**, editado
por el responsable después del ensayo E. Solo cambió esa cadena; descripción,
tarjeta Iniciar sesión, ojo, autenticación y estilos se conservaron. F ejecutó
6 pruebas focales de login, lint/build y19 comprobaciones Edge del build con API
ficticia. No atribuir el título nuevo a la imagen E ni a sus80/26 integradas:
reconstruir el frontend desde el SHA publicado. Backend, API36, seis migraciones,
locks y configuración Docker/Azure siguen iguales; evidencia E se reutiliza por
huellas, sin repetir inicialización SQL, migraciones o bootstrap. No hay Azure.


# HISTÓRICO — Cortes anteriores conservados, no estado actual

Las declaraciones siguientes pertenecen a sus cortes documentales y no sustituyen
la sección VIGENTE. Se conservan para trazabilidad, no como nuevas verificaciones.

### Corte del ensayo Docker anterior a Macro C — 20/11/2026

La plataforma Vanilla + Flask/Gunicorn + MySQL funcionó en un proyecto Docker
nuevo con HTTPS loopback, roles, formularios, datos ficticios y persistencia.
Se aplicaron las seis revisiones solo sobre recon_container_0010 del volumen
nuevo. No se conectaron ni migraron bases Windows. El ensayo fue apagado sin -v.

Bases linux/amd64: Python 3.14.10, Node 26.13.1 y Nginx 1.30.7, por digest.
Gunicorn 25.3.0 pertenece a una rama mantenida; Flask/ORM/Python mayor intactos.
Frontend: Vite 7.3.8/Vitest 3.2.7; Bootstrap 5.3.8. Las 190 pruebas frontend,
20 de adaptador, lint/build, HTTPS/API y Edge aportan evidencia local; no Azure.
Audit producción cero; tres paquetes dev con avisos residuales se aíslan fuera
del runtime. Seguridad completa de capas, firmas/SBOM, configuración pública y
resolución definitiva de deuda dev requieren revisión independiente.

Única publicación local 127.0.0.1:8443; API8000 y DB3306 internos. Web/data
internas más entrada_local exclusiva de Nginx, loopback y sin masquerade.
Cookies HttpOnly/Secure/SameSite y CSRF comprobados. TLS autofirmado de laboratorio:
confianza privada por CA local en Python y SPKI acotado en Edge, sin modificar
el almacén global Windows. No trasladar estas excepciones como TLS público.

La factory de CLI app_wsgi:create_cli_app carga *_FILE y rechaza destinos ajenos
al contrato; no hace upgrades ni bootstrap automáticamente. Se mantienen los
contratos HTTP, los seis dominios y la separación Persona/cuenta/biometría.
React legado y candidata permanecen preservados. No hay hardware facial integrado.

[Guía y pruebas del ensayo](../pruebas/DOCKER_LOCAL_0010.md),
[operación Docker](../../deploy/README.md). El paquete externo de revisión aporta
digests/IDs, manifiestos, evidencias y comandos reales. Reproducibilidad binaria
de pip completa y publicación de imágenes no se presumen por fijar versiones.

G6 Windows continúa pendiente de credencial vigente y causa concreta del 1045;
Docker no lo cierra. C15/D08/D09/D13 y D12 humana continúan abiertos. No hay commit
nuevo ni push; Azure deberá usar el commit que publique el responsable después
de revisar. DNS, TLS público, secretos de producción, red, readiness de esquema,
recursos/costos y despliegue Azure requieren encargo independiente.

## Corte histórico Macro B — preparación estática conservada

### Estado declarado al corte Macro B — 20/11/2026

Macro A aprobado técnicamente con reservas. Se prepararon
[Compose](../../compose.yaml), [Dockerfile backend](../../backend/Dockerfile),
[Dockerfile frontend](../../frontend/Dockerfile) y
[Nginx](../../frontend/nginx.conf), con
[guía operativa y permisos pendientes](../../deploy/README.md).
Son candidatos estáticos: no se construyeron imágenes, instalaron paquetes,
levantaron contenedores ni ejecutaron migraciones.

Validación actual: Compose config --quiet PASS con fixtures inertes externas,
diez comprobaciones estructurales y 17 tests nuevos del adaptador WSGI PASS;
Ruff PASS. Docker CLI/Compose presentes, motor Linux no disponible;
hadolint/nginx -t, disponibilidad de etiquetas/digests y build/up NO EJECUTADOS.
Las etiquetas propuestas y Gunicorn deben verificarse y aprobarse antes del
build; no hay certificación de compatibilidad Linux/producción.

G6: E0 y delta auxiliares PASS sin secretos/servicios/DB. C0 recibió MySQL 1045
antes de cualquier SELECT; identidad/esquema NO VERIFICADOS. STOP B1, sin probar
otros passwords, permisos o bootstrap. Cero claves generadas y cero servicios
G6 iniciados. No se presume que el error sea exclusivamente de contraseña;
también requiere revisión del canal/cuenta/destino por el responsable.
No reanudar G6 por leer este contrato.

El stack propuesto sirve HTTPS solo en 127.0.0.1:8443; API:8000 y MySQL no se
publican. Redes web/data internas y volumen nuevo de proyecto. Usa una DB y
cuenta nuevas (`recon_container_0010`, `recon_container_app`), nunca las Windows.
El perfil approved-runtime y permisos de contenedores, inicialización,
migraciones, secretos/TLS y descargas siguen pendientes por separado.

La [entrada WSGI](../../backend/deploy/app_wsgi.py) exige destino de contenedor,
Secure/HTTPS y archivos montados; mantiene factory/código/API/RBAC originales.
Acepta X-Forwarded-Proto solo desde el servicio frontend, no headers del cliente.
Gunicorn propone Linux; no se instaló en Windows ni se cambió pyproject.

Variables de contenedor adicionales, solo nombres: `DB_PASSWORD_FILE`,
`SECRET_KEY_FILE`, `RECON_DB_ROOT_PASSWORD_FILE`, `RECON_DB_APP_PASSWORD_FILE`,
`RECON_SESSION_KEY_FILE`, `RECON_TLS_CERT_FILE`, `RECON_TLS_KEY_FILE`,
`RECON_PYTHON_IMAGE`, `RECON_NODE_IMAGE`, `RECON_NGINX_IMAGE`,
`RECON_MYSQL_IMAGE`, `RECON_HTTPS_PORT`. La
[plantilla](../../deploy/container.env.example) no contiene valores secretos.
No se crean archivos privados nuevos ni certificados en esta fase.

Healthchecks son liveness, no readiness de esquema/login. La DB nueva necesita
inicialización autorizada y luego migraciones/fixtures revisados: nada se aplica
silenciosamente al arrancar Flask. Sesiones stateful, CSRF y cookies permanecen.
DNS de Azure, hosts Nginx, TLS público, puertos, WSGI/imágenes y pruebas reales
requieren revisión posterior sobre un commit efectivamente publicado por el
usuario. No hay commit ni recurso Azure nuevo. Incremento 0010 ABIERTO.

## Corte histórico de preparación Macro A — conservado

Este documento describe código local observado del Incremento 0010, Macro A.
No prueba despliegue, Docker o G6. No hay commit nuevo: el árbol conserva cambios
locales, y solo el usuario publicará una versión revisada. El chat Azure deberá
usar el SHA realmente publicado, nunca el nombre de una entrega como commit.

## Repositorio y stack

Un repositorio contiene [backend](../../backend/) y [frontend](../../frontend/).
Backend declara Python >=3.14,<3.15, Flask 3.1.3, SQLAlchemy 2.0.54,
Flask-SQLAlchemy 3.1.1, Alembic 1.20.0, Flask-Migrate 4.1.0 y PyMySQL 1.2.2;
fuente canónica: [pyproject.toml](../../backend/pyproject.toml).
No se selecciona servidor WSGI ni imagen final desde esta fase.

Frontend vigente: JavaScript Vanilla, Bootstrap 5.3.8, Vite 7.1.12 para build,
sin React/ReactDOM/JSX en runtime. [Lock](../../frontend/package-lock.json) y
[manifiesto](../../frontend/package.json) fijan dependencias. La candidata y
React legado son respaldo, no contextos productivos.

## Arranque, API y rutas

La [factory](../../backend/src/recon_platform/__init__.py) es
`recon_platform:create_app`, con `pruebas=False` por defecto. El controlador de
integración debe elegir `pruebas=True` de forma explícita; no ejecutar un
`flask run` genérico con variables de desarrollo para probar.

La [especificación](../../backend/openapi.json) usa `servers.url=/api/v1` y
35 operaciones. Las rutas concretas relativas del contrato se anteponen a esa
base; no omitirla al comparar con Flask. Hay ocho blueprints. El diagnóstico
existente es `GET /_diagnostico`, sin autenticación, con estado inicializado;
no consulta MySQL y **no es readiness de base ni un `/health` ya implementado**.
El puerto de proceso Flask se fija por el runner, no en la factory.

Desarrollo/ensayo aprobado usa loopback API:5000 y Vite:5173; Vite tiene proxy
`/api/v1` a la API y fallback SPA. La configuración de producción futura debe
servir estáticos con fallback de enlaces profundos, conservar misma raíz/origen
para API y establecer TLS antes de exponer credenciales fuera de loopback.
No se implementó Nginx, Compose, proxy confiable o publicación de puertos aquí.

## Variables — solo nombres

`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_TEST_NAME`,
`DB_TEST_USER`, `DB_TEST_PASSWORD`, `SECRET_KEY`, `RECON_LOCAL_HTTP`,
`RECON_SESSION_COOKIE_SECURE`. Se leen en
[configuración](../../backend/src/recon_platform/config.py) y factory.
`FLASK_SKIP_DOTENV` es control auxiliar del ensayo, no secreto de aplicación.
No hay una variable VITE de backend que sea necesaria por el código actual:
el cliente usa rutas relativas `/api/v1`. No inventar variables CORS ni
transferir valores del documento privado al chat Azure, imagen o ZIP.

## Sesiones y permisos

El backend valida roles y CSRF; no confiar en los guards UI. Sesiones stateful,
identificador opaco, cookie `recon_session`, HttpOnly, SameSite Lax y ruta
`/api/v1`, Secure por defecto. La excepción sin Secure requiere HTTP local
expreso y host loopback; no constituye una política de producción.
No JWT humano en localStorage, registro público, nueva SUPERADMIN automática o
SECRET_KEY fija. La clave privada se suministra por entorno, nunca por CLI o docs.

Persona y cuenta son distintas. Desactivar no anonimiza. No hay DELETE físico
aprobado ni integración facial física. G6 solo puede operar recon_tests con
cuenta y permisos restringidos y sus gates; Macro A no lo ejecutó. Una futura
base de contenedor deberá ser nueva/aislada, no compartir volúmenes, puertos o
secretos del MySQL de Windows, ni deducir permiso de migración por este texto.

## Migraciones, empaquetado y pendientes

Las [seis revisiones existentes](../../backend/migrations/versions/) permanecen
intactas. No se ejecutó `current`, `upgrade`, `migrate`, ALTER o conexión real.
La importación del archivo Alembic env no es una comprobación inerte: su cuerpo
ejecuta el entorno de migración. Revisar y autorizar el procedimiento aparte.

[.dockerignore](../../.dockerignore) prepara exclusiones para un contexto **raíz
del repo**, sin ejecutar Docker: secretos locales, Git, entornos, cachés,
node_modules/dist Windows y ambos respaldos frontend. No elimina fuentes.
Si la fase B elige contextos separados deberá revisar exclusiones por contexto.

Pendientes: revisión Macro A, E0/C0 y G6 reales, reservas C15/D08/D09/D13/D12,
selección WSGI, Dockerfiles/Compose/Nginx, imágenes construibles, base aislada,
TLS/origen/proxy y pruebas de contenedores. Azure, VM, DNS, NSG, recursos,
costos y video pertenecen al trabajo posterior separado. Ningún recurso está
confirmado como creado por este documento. Incremento 0010 ABIERTO.
