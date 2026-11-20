# Docker local — ensayo aislado del Incremento 0010

## Resultado vigente 20/11/2026

Ensayo local completo ejecutado sobre un proyecto y volumen nuevos. HTTPS en
127.0.0.1:8443, Nginx 1.30.7, Flask/Gunicorn 25.3.0 con Python 3.14.10 y MySQL
aislado. Bases fijadas por digest en [Compose](../compose.yaml) y Dockerfiles.
Node 26.13.1 reutilizado; Vite 7.3.8 y Vitest 3.2.7 actualizados en el lock.

Pasaron 190 pruebas frontend (189 anteriores y una regresión de foco nativo),
ESLint/build, 20 pruebas del adaptador, Ruff y pruebas reales HTTPS/navegador.
Se verificaron login/roles/CSRF/cookies, formularios, cinco Personas ficticias,
cinco eventos manuales, incidencias y persistencia tras parada/reinicio.
El volumen se conservó; los servicios del ensayo quedaron apagados sin -v.

Audit de producción: cero vulnerabilidades reportadas. Audit completo: tres
paquetes dev afectados, con dos clasificaciones críticas y una moderada.
Se admiten solo para este ensayo bajo mitigaciones: sin secretos ni red durante
tests, sin UI/API Vitest, y runtime Nginx sin Node/node_modules/dev servers.
No constituye certificación de seguridad de producción ni auditoría de capas OS.

API/DB permanecen en web/data internas sin puertos host. Nginx añade una red
entrada_local con binding loopback y sin masquerade, necesaria para publicar
HTTPS en Docker Desktop. No se cambió la red del host ni ningún recurso ajeno.

[Validación, guía y limitaciones](../docs/pruebas/DOCKER_LOCAL_0010.md).
Los secretos nuevos se conservan en almacenamiento privado externo; nunca en
este repositorio, imágenes o ZIP. El adaptador ofrece create_cli_app para CLI
con lectura *_FILE y comprobación estricta del destino; no migra al importar.
La SUPERADMIN de esta DB nueva se creó mediante la CLI oficial, no por SQL manual.

G6 Windows sigue bloqueado; no hubo conexiones nuevas a sus bases. Permanecen
C15/D08/D09/D13 y D12 humana; el atajo 200% headless no produjo zoom real y no
se marca PASS. Azure, Macro C, Git de escritura y cierre no se ejecutaron.
Incremento 0010 ABIERTO. El registro siguiente es histórico y no revoca las
autorizaciones específicas del ensayo posterior.

## Corte histórico Macro B — preparación estática conservada

**No se ha construido ni ejecutado este stack.** El motor Linux de Docker
Desktop no respondió en la verificación. Esta fase solo autoriza archivos y
validación estática. El Incremento 0010 permanece abierto; no hay despliegue Azure.

## Estructura y aislamiento

| Servicio | Función | Exposición |
|---|---|---|
| frontend | Nginx sin root, SPA compilada Vanilla, TLS y proxy API | Solo `127.0.0.1:8443`, HTTPS con certificado externo |
| backend | Python 3.14, Gunicorn propuesto, factory Flask | Puerto 8000 interno, sin publicación al host |
| db | MySQL nuevo, aislado, persistencia propia | Sin puerto al host ni vínculo con MySQL Windows |

[Compose](../compose.yaml) usa redes web/data internas, secretos por archivo
externo y volumen propio del proyecto `recon-inc0010-isolated`. Antes del primer
arranque verificar que no exista un proyecto/volumen previo con ese nombre;
no reutilizarlo silenciosamente. No se comparten recon_dev, recon_tests, puertos,
volúmenes o contraseñas de Windows. Los tres servicios requieren el perfil
`approved-runtime`: una orden de arranque genérica no selecciona servicios.

Ambos contextos de build son la raíz del repositorio. Los archivos
[backend/Dockerfile.dockerignore](../backend/Dockerfile.dockerignore) y
[frontend/Dockerfile.dockerignore](../frontend/Dockerfile.dockerignore) aplican
whitelists específicas, con secretos/cachés excluidos. El frontend copia solo
manifiestos/lock/config/entrada/src: no React, candidata, instalación o dist Windows.

## Dependencias e imágenes pendientes de verificación

Las versiones directas del backend permanecen en
[pyproject.toml](../backend/pyproject.toml). El
[snapshot runtime](../backend/deploy/requirements-runtime.txt) fija también
transitivas observadas, evaluando sus marcadores para Linux x86_64/Python 3.14.
No se cambia el entorno Windows ni el empaquetado del proyecto: la imagen
instala dependencias y carga las fuentes canónicas por PYTHONPATH.

[Gunicorn 23.0.0](../backend/deploy/requirements-wsgi.txt) es una **propuesta
exclusiva de contenedor Linux**, todavía no instalada ni comprobada con
CPython 3.14. Packaging conserva la versión local observada. Su compatibilidad,
revisión de seguridad y wheels deberán verificarse antes de construir/aprobar
el runtime. No se recomienda esta imagen como producción validada por crear
los archivos. `--only-binary=:all:` falla si falta un wheel; no compila fuentes
de dependencia por sorpresa.

Las etiquetas candidatas Python/Node/Nginx/MySQL están en la
[plantilla](./container.env.example). **Su disponibilidad no está confirmada**;
no se consultó el registro. MySQL `8.4` es una familia mutable, no un digest.
Antes de build, autorizar las descargas/instalaciones necesarias, revisar versiones
y sustituirlas por `tag@sha256:...` verificadas. El snapshot de versiones y el
lock npm no bastan por sí solos para reproducibilidad binaria sin esos digests
y artefactos Linux comprobados.

## TLS, cookies y secretos

El backend exige cookie Secure y HTTPS. La excepción HTTP local de Windows no
funciona por conveniencia a través de una red de contenedores y no se relajó.
Nginx declara su esquema; el adaptador WSGI solo acepta ese dato si el peer
coincide con el servicio frontend resuelto por DNS interno. No confía en
X-Forwarded-For/Host de clientes. Si DNS/proto/peer no coinciden, falla cerrado.
Las pruebas nuevas verifican la lógica, no la resolución Docker real.

El certificado debe ser válido/confiable para localhost/127.0.0.1 en la demo.
No se generaron certificados, claves TLS ni secretos persistentes. La plantilla
solo declara rutas vacías para cinco archivos externos: contraseña root de la
DB nueva, contraseña de su cuenta nueva, clave de sesiones nueva, certificado
y clave TLS. No apuntarlos al documento mixto de contraseñas ni reutilizar los
secretos de recon_tests. Su provisión privada requiere autorización aparte.
No escribir valores en `.env`, argumentos CLI, imágenes, logs, Git o ZIP.

El backend carga exclusivamente archivos bajo `/run/secrets`; ni Dockerfile
ni Compose contienen passwords/SECRET_KEY baked. La clave persistente del stack
futuro es distinta del cupo efímero G6: esta preparación no genera ninguna.

## Healthchecks y esquema

`/_diagnostico` prueba proceso/factory, no DB. El healthcheck de Nginx prueba
solo su proceso en el puerto 8080 interno, sin publicación HTTP. `mysqladmin
ping` es liveness del motor y puede dar vivo aunque falte autenticación; no es
validación de esquema/identidad. Dependencias healthy no acreditan login.

La imagen MySQL inicializará una DB vacía nueva al primer arranque autorizado.
**Esto también necesita permiso de inicialización**, además de B2-RUN-LOCAL.
No hay `flask db upgrade` ni seeds/bootstrap en el arranque. Las seis revisiones
se copian para un procedimiento futuro revisado; ejecutarlas y crear cuentas
ficticias exige autorización independiente. No emplear el CLI genérico contra
MySQL de Windows.

## Comprobaciones que sí se ejecutaron

Desde raíz, sin motor ni servicios:

```powershell
python -B scripts/validar_docker_estatico.py
```

El script construye fixtures **inertes externas**, limpia variables heredadas y
ejecuta `docker compose --env-file deploy/container.env.example -f compose.yaml
config --quiet`. No imprime un config interpolado ni usa secretos reales. Los
fixtures se retiran con el contexto temporal únicamente dentro de su directorio.
Valida diez propiedades estructurales; no sustituye `hadolint` o `nginx -t`,
que no estaban disponibles. Las 17 pruebas de adaptador y Ruff pasaron.

## Pasos futuros, no ejecutados ni autorizados aquí

1. Obtener aprobación separada de B2-RUN-LOCAL, provisión TLS/secretos, imágenes,
   instalaciones/descargas y DB inicialización/migraciones/fixtures.
2. Iniciar Docker Desktop solo tras permiso, comprobar Linux, versiones, espacio,
   redes y ausencia de colisiones de proyecto/volumen. Inventariar imágenes locales.
3. Verificar imágenes/digests y wheels. Si falta contenido, detener sin descargar
   hasta autorización de red/instalación. Proveer archivos secretos externos.
4. Revalidar Compose `--quiet` con canal privado, luego builds autorizados.
   Comprobar `nginx -t`, usuario no root, exclusiones, TLS, origen y healthchecks.
5. Arranque inicial de db solo con permiso de inicialización. Verificar su
   identidad nueva, esquema y migraciones previstas antes de autorizar cambios.
   Nunca bootstrap automático ni operaciones sobre bases Windows.
6. Con datos ficticios autorizados, levantar backend/frontend y realizar E2E
   HTTPS, sesiones/CSRF/RBAC, enlaces profundos, persistencia ante reinicio y
   conciliación. No heredar permisos de escritura G6 a la DB de contenedor.
7. Cerrar solo el proyecto propio con `docker compose --profile approved-runtime
   down`, **sin -v**. Conservar volumen y respaldos; nunca prune o limpieza ajena.

Las órdenes de build/up no se ejecutan como parte de este documento. Una base
vacía sin migraciones aprobadas no constituye una demo funcional. Azure requerirá
DNS/TLS/hosts/configuración y commit publicado propios, con otro encargo.

Ejemplos para la fase futura **solo después de aprobar cada puerta**, usando el
mismo archivo externo de rutas no secretas durante todo el ciclo:

```powershell
# RUTAS_EXTERNAS es un archivo de rutas/etiquetas, sin valores de passwords o keys.
docker compose --env-file RUTAS_EXTERNAS config --quiet
# Requiere permiso de build e instalaciones; también red si faltan artefactos.
docker compose --env-file RUTAS_EXTERNAS --profile approved-runtime build --pull=false
# Requiere B2-RUN-LOCAL e inicialización de DB nueva, aun sin tablas de aplicación.
docker compose --env-file RUTAS_EXTERNAS --profile approved-runtime up -d --no-build --pull never db
# STOP aquí: revisar identidad, migraciones y fixtures mediante encargo propio.
# Solo después del esquema/cuentas aprobados y verificados:
docker compose --env-file RUTAS_EXTERNAS --profile approved-runtime up -d --no-build --pull never backend frontend
# Cierre del proyecto propio conservando volumen:
docker compose --env-file RUTAS_EXTERNAS --profile approved-runtime down
```

No se aporta un `upgrade` automático ni un bootstrap en estos ejemplos. El CLI
de migración deberá cargar secretos en memoria y verificar la DB nueva mediante
un procedimiento específico revisado; la factory original no interpreta
variables `*_FILE` por sí sola. No copiar comandos del host Windows para evitar
ese paso. Ni `RUTAS_EXTERNAS` ni los cinco archivos privados se crearon aquí.
