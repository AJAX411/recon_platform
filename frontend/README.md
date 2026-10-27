# Frontend 0007-A, 0007-B y 0008 · Recon Facial

Interfaz React para autenticación humana, administración de Personas, Usuarios, Puntos de Acceso y Dispositivos Edge, y registro/consulta de Eventos de Acceso manuales. El contrato es el de [`../backend/openapi.json`](../backend/openapi.json); no incluye enrolamiento biométrico ni comunicación física con dispositivos.

## Requisitos y puesta en marcha local

- Node.js 22.12+ para Vite 7.1.12 (`^20.19.0 || >=22.12.0`); Vitest 3.2.4 y React Router DOM 7.9.4 también admiten Node 22.14.0. Se verificaron build, lint y pruebas con Node 22.14.0 y npm 10.9.2. **Node 24 LTS continúa como baseline provisional del proyecto** y no se probó en este entorno; la compatibilidad declarada por las dependencias no sustituye una validación futura en Node 24. No se instaló ni actualizó Node globalmente.
- Backend Flask configurado con MySQL propio del responsable, `SECRET_KEY` de al menos 32 bytes, `DB_HOST=127.0.0.1`, `RECON_LOCAL_HTTP=1` y `RECON_SESSION_COOKIE_SECURE=0` **solo en desarrollo HTTP local**. Seguir [`../backend/README.md`](../backend/README.md) para configurar y arrancar Flask. No se crea ni modifica ninguna base al arrancar el frontend.
- Flask debe escuchar solo en `127.0.0.1:5000`. Vite escucha solo en `127.0.0.1:5173`; abrir exactamente `http://127.0.0.1:5173` en el navegador.

Con las variables del backend ya configuradas por el responsable, arrancar Flask desde `backend/`:

```powershell
& '.\.venv\Scripts\python.exe' -B -m flask --app recon_platform:create_app run --host 127.0.0.1 --port 5000
```

```powershell
cd frontend
npm ci
npm run dev
```

Vite pasa únicamente `/api/v1` a `http://127.0.0.1:5000` con el host de destino correcto. El navegador hace peticiones al mismo origen de Vite; no se necesita CORS ni se exponen cookies a JavaScript. La cookie `HttpOnly` de Flask tiene ruta `/api/v1` y `SameSite=Lax`. Fuera del modo local, Flask exige HTTPS y cookie `Secure`; la configuración de producción y su terminación TLS quedan pendientes.

`npm run dev` inicia un proceso persistente: durante esta revisión Vite informó `ready in 507 ms` y sirvió `/` con HTTP 200. El ejecutor informó código de salida 1 después de detenerlo deliberadamente con Ctrl+C; ese código no indica un fallo de arranque. Si Flask no está en `127.0.0.1:5000`, las llamadas a `/api/v1` producen `ECONNREFUSED` en el proxy y la interfaz muestra el error HTTP 500 resultante; es una condición distinta del arranque de Vite.

## Flujo de sesión

La aplicación consulta `/auth/me` al cargar. Para el login obtiene antes `/auth/csrf`, envía `X-CSRF-Token` y conserva en memoria el token renovado en la cabecera de la respuesta. Para cualquier escritura posterior obtiene un token nuevo si la página fue recargada. La sesión se guarda exclusivamente en la cookie opaca del backend; ni la sesión ni el CSRF se guardan en `localStorage`. El cierre de sesión revoca la sesión con CSRF.

Las rutas de Personas se muestran solo para SUPERADMIN y ADMINISTRADOR. Usuarios corresponde solo a SUPERADMIN. Puntos de Acceso y Dispositivos Edge pueden consultarse por los tres roles; crear y editar corresponde a SUPERADMIN/ADMINISTRADOR; cambiar estado y modo (en Dispositivos Edge) corresponde a los tres roles según las API existentes. Flask vuelve a validar sesión, rol y CSRF; el control del navegador es únicamente de navegación.

## Módulos de 0007-B

| Rutas | Funciones |
|---|---|
| `/usuarios`, `/usuarios/nuevo`, `/usuarios/:id` | Listado paginado, consulta, creación de ADMINISTRADOR/OPERADOR, cambio de rol y estado. Los roles asignables provienen de `/api/v1/iam/roles`. SUPERADMIN inicial protegido. |
| `/puntos-acceso`, `/puntos-acceso/nuevo`, `/puntos-acceso/:id` | Listado con filtros `codigo`/`estado`, consulta, creación, edición de nombre/descripción y cambio de estado. |
| `/dispositivos-edge`, `/dispositivos-edge/nuevo`, `/dispositivos-edge/:id` | Listado con filtros `codigo`/`estado`/`modo_operacion`/`id_punto_acceso`, consulta, registro con ID de Punto de Acceso, edición de nombre, cambio de estado y modo. |

Los listados usan 20 registros por página y la API no proporciona total. Los dispositivos nuevos se muestran con el estado que devuelve Flask (`INACTIVO` según la implementación actual). El estado administrativo y `ultima_comunicacion` no constituyen una prueba de conexión o funcionamiento físico. La aplicación envía la contraseña inicial solo en la solicitud HTTPS o HTTP local autorizado y no la escribe en almacenamiento persistente del navegador.

## Incremento 0008 — Eventos de Acceso manuales

| Ruta web | Función y permisos |
|---|---|
| `/eventos-acceso/manual` | Los tres roles buscan Personas activas en el selector específico, eligen Punto activo paginado y declaran ENTRADA/SALIDA con confirmación. |
| `/eventos-acceso/historial` | OPERADOR ve solo movimiento, resultado y hora aproximada de la jornada Bogotá, sin filtros administrativos; ADMINISTRADOR/SUPERADMIN consultan histórico ampliado paginado y filtrable. |
| `/eventos-acceso/alertas` | OPERADOR ve conteos agregados del día; ADMINISTRADOR/SUPERADMIN ven incidencias ampliadas paginadas y filtrables. Actualización manual. |
| `/eventos-acceso/incidencias/:id` | Detalle personal solo para ADMINISTRADOR/SUPERADMIN. Flask revalida la autorización; OPERADOR no monta esta página. |

El registro utiliza la sesión humana y CSRF existentes. Cada declaración confirmada lleva una clave `Idempotency-Key` UUIDv4 generada una sola vez; el cliente conserva en memoria clave, actor y cuerpo inmutable para un reintento **explícito** tras un resultado incierto. Una barrera síncrona impide dos envíos simultáneos. `201` indica evento nuevo y `200` recupera el ya registrado. No hay reintentos automáticos ni persistencia de clave, sesión o datos de la declaración en almacenamiento del navegador. Al recargar se pierde la clave: si el resultado era incierto, se debe consultar con un administrador antes de declarar otra vez el mismo movimiento. La aplicación advierte antes de salir cuando puede detectar una declaración pendiente, sin prometer recuperación tras recarga.

La búsqueda de Personas admite `nombre`, `documento` o `institucional` y devuelve hasta 20 resultados; el Punto se consulta con `estado=ACTIVO` y el backend verifica ambos estados otra vez al registrar. El GET de búsqueda transporta el valor en la query: la interfaz no lo copia a rutas React ni a almacenamiento persistente. **El saneamiento de logs HTTP queda pendiente de verificación antes de operar con datos personales reales.** Los filtros administrativos de fechas se interpretan como días civiles de `America/Bogota` y envían un límite `hasta` exclusivo; la zona del navegador no interviene. El registro MANUAL no demuestra presencia real, reconocimiento facial ni apertura de puertas.

El [manifiesto 0008](./INCREMENTO_0008_BLOQUE1_PROPUESTA.md) contiene permisos, errores, exclusiones y criterios de aceptación aprobados para este incremento. La revisión independiente y cualquier validación manual con backend/MySQL reales corresponden al Bloque 3; Codex no accede a MySQL en el Bloque 2.

Cuando una página posterior está vacía, «Anterior» permanece disponible y «Siguiente» queda deshabilitado; no se infiere un total inexistente. La desactivación de cuentas y los cambios de estado de Puntos o Dispositivos y de modo de Dispositivos muestran una confirmación en línea. «Cancelar» devuelve el foco al control de origen y no envía la operación; confirmar usa la misma API y el mismo CSRF.

## Comprobaciones

```powershell
npm run build
npm run lint
npm test
```

Las pruebas del frontend usan datos ficticios y sustitutos de `fetch`; no acceden a MySQL. Para validar manualmente: iniciar Flask con la configuración local, abrir Vite, comprobar login válido e inválido, recargar y confirmar recuperación de sesión, cerrar sesión, repetir con un rol OPERADOR, y con ADMINISTRADOR o SUPERADMIN probar filtros, consulta, registro y errores de validación o duplicidad. Inspeccionar Network para confirmar que la cookie es `HttpOnly`, `Path=/api/v1`, que login devuelve y utiliza un CSRF rotado y que no hay llamadas CORS. No usar datos personales reales para esta validación.

Para validar 0007-B con un entorno de datos de prueba controlado por el responsable: entrar como SUPERADMIN y comprobar Usuarios, creación de una cuenta ADMINISTRADOR/OPERADOR ficticia, cambio de rol/estado y protección de la cuenta SUPERADMIN. Entrar como ADMINISTRADOR y OPERADOR para comprobar navegación y denegaciones. Con Puntos y Dispositivos ficticios autorizados, revisar filtros, páginas, consulta, creación, edición, estado y modo; confirmar que cada escritura incluye `X-CSRF-Token`. Verificar que la ficha de un dispositivo nuevo indica el estado devuelto por Flask y no afirma conexión. Consultar [`INCREMENTO_0007-B.md`](./INCREMENTO_0007-B.md) para el alcance y límites. Estas acciones manuales no se ejecutaron durante el desarrollo.

Para validar accesibilidad: pulsar Tab al cargar para llegar a «Saltar al contenido principal», pulsar Enter y comprobar que el foco llega a `main`; navegar entre Inicio y Personas y comprobar el foco en el contenido y el título del documento. Repetir en pantalla estrecha y con lector de pantalla. Los tests automatizados cubren el enlace de salto y el foco en los cambios de ruta, pero no sustituyen esa comprobación manual.

La API de listado no devuelve total; el botón «Siguiente» se habilita cuando la página contiene el límite de 20 registros y una página adicional puede resultar vacía. El catálogo definitivo de tipos de documento, las reglas especiales pendientes para otras categorías, el protocolo y autenticación Edge, la operación offline y el despliegue TLS quedan fuera de estos incrementos.
