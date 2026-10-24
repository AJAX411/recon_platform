# Manifiesto de alcance · 0007-B

## Fuentes y punto de partida

- Baseline vigente: **CONTEXTO MAESTRO — PROYECTO RECON FACIAL — v1.5**. Objetivo y contexto institucional CONFIRMADOS; arquitectura lógica Edge + Plataforma, monolito modular, modelo lógico y stack React/Vite/Bootstrap PROVISIONALES; detector y embedder EN INVESTIGACIÓN; contrato Edge, operación offline y despliegue PENDIENTES.
- Resolución posterior **Independencia entre UsuarioPlataforma y Persona** (PROVISIONAL — APROBADA PARA IMPLEMENTACIÓN): sustituye únicamente la vinculación obligatoria de la sección 20 para el prototipo. Solo SUPERADMIN administra cuentas y roles. No se crea vínculo cuenta–Persona.
- La frontera de administración web se cotejó con [`../backend/openapi.json`](../backend/openapi.json), los controladores y casos de uso de Identity/IAM, PuntoAcceso y DispositivoEdge. Los detalles de endpoint y payload son los implementados allí; no definen el protocolo ni la autenticación Edge.
- Inicio: rama `main`, commit `e9728d6`, árbol limpio. 0007-A está cerrado técnicamente. Node.js 22.14.0 y npm 10.9.2 presentes; Node 24 LTS continúa como baseline PROVISIONAL y no se instala globalmente.

## Alcance aprobado y criterios

- Usuarios: listado y consulta; creación exclusiva de ADMINISTRADOR/OPERADOR; cambio de rol y estado solo de cuentas administrables; catálogo de roles desde `/api/v1/iam/roles`. Solo SUPERADMIN.
- Puntos de Acceso: listado con filtros `codigo` y `estado`, consulta, creación, edición de `nombre`/`descripcion`, cambio de estado. Los tres roles consultan y cambian estado; SUPERADMIN/ADMINISTRADOR crean y editan.
- Dispositivos Edge: listado con filtros `codigo`, `estado`, `modo_operacion`, `id_punto_acceso`; consulta, registro administrativo con punto existente, edición de `nombre`, cambio de estado y modo. Los tres roles consultan y cambian estado/modo; SUPERADMIN/ADMINISTRADOR crean y editan.
- Las listas utilizan `limite` y `desplazamiento` (1–100 y 0–1 000 000) y no reciben total. Todas las escrituras usan el cliente HTTP con cookie HttpOnly y CSRF. Los errores del servidor se muestran sin fabricar datos.
- Criterios de aceptación: navegación por rol; permisos visuales y validación efectiva del backend; formularios accesibles; carga, vacío, éxito y error; paginación; pruebas automatizadas sin MySQL; build, lint y tests aprobados; documentación de validación manual.

## Límites

- No se modifica backend, OpenAPI, migraciones ni MySQL. No se crean cuentas ni dispositivos reales durante la implementación.
- `estado` de DispositivoEdge es administrativo; `ultima_comunicacion` es un dato histórico nullable. La interfaz no infiere conexión, funcionamiento ni biometría.
- No hay vínculo automático entre cuentas y Personas ni funciones de Raspberry, reconocimiento o enrolamiento.
- La matriz completa de permisos, la autenticación Edge, la operación offline y el despliegue permanecen PENDIENTES fuera de este incremento.

## Verificación del incremento

- El frontend conserva las pruebas de 0007-A. Las pruebas nuevas usan exclusivamente datos ficticios y sustitutos de la API para sesión, permisos, CSRF, listados, paginación, filtros, validación, cuenta SUPERADMIN protegida, cambios de estado/modo y errores HTTP.
- La revisión independiente 0007-B motivó dos ajustes puntuales: los controles de paginación siguen visibles en páginas vacías y un panel accesible confirma la desactivación de cuentas y los cambios administrativos de estado/modo antes de enviar la solicitud. Cancelar no envía HTTP y los permisos del backend permanecen iguales.
- La corrección final de paginación extiende el control compartido también a Personas: desde una segunda página vacía se puede volver con «Anterior», mientras «Siguiente» queda deshabilitado. No se infiere un total de registros.
- Los ajustes de consistencia UX/UI mantienen «Aplicar filtros» como acción principal y muestran «Limpiar» con borde secundario en Personas, Puntos y Dispositivos. Las cuatro fichas de detalle muestran un único indicador ACTIVO/INACTIVO junto al título de sus datos administrativos. Cambiar rol, editar nombre/descripción de Punto y editar nombre de Dispositivo requieren confirmación en la misma sección solo cuando hay cambios efectivos; cancelar no escribe y el foco regresa al botón de origen. Las operaciones de estado y modo conservan sus confirmaciones anteriores.
- En Node.js 22.14.0, `npm run build` compila el frontend, `npm run lint` termina sin hallazgos y `npm test` aprueba 48 pruebas en seis archivos tras estos ajustes. Se preservaron las pruebas de 0007-A.
- La revisión visual con respuestas ficticias comprobó navegación, listados y tablas a 1440 y 390 px; a 390 px la navegación y las tablas se desplazan dentro de sus contenedores sin ampliar el documento. Los cambios de ruta enfocaron el contenido principal. Esta revisión se limita a la interfaz del navegador.
- La revisión de navegador con datos ficticios comprobó las fichas y filtros a 1440 y 390 px: el estado comparte fila cuando cabe y pasa a la siguiente en pantalla estrecha, sin desbordamiento horizontal del documento. El responsable comunicó una validación funcional real favorable de 0007-B antes de estos ajustes; Codex no la repitió ni accedió a MySQL en esta sesión.
- Dashboard, Raspberry, biometría y rediseño global permanecen diferidos. Una futura dirección visual requiere revisión y aprobación del prototipo del responsable y referencias de diseño; esta entrega no cierra decisiones PROVISIONALES ni PENDIENTES.
