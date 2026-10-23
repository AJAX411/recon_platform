# Manifiesto de alcance · 0007-A

## Fuentes y vigencia

- Baseline: **CONTEXTO MAESTRO — PROYECTO RECON FACIAL — v1.5**. La lectura completa del archivo recuperado y el cotejo con el frontend se completaron durante la revisión independiente 0007-A. Sus estados documentales se conservan: objetivo y contexto institucional CONFIRMADOS; arquitectura lógica, monolito modular, modelo y stack PROVISIONALES; componentes biométricos EN INVESTIGACIÓN; contratos y reglas no cerrados PENDIENTES.
- Resolución **Independencia entre UsuarioPlataforma y Persona** (15 de octubre de 2026, PROVISIONAL — APROBADA PARA IMPLEMENTACIÓN): cuentas y Personas independientes; un rol por cuenta; autenticación humana con contraseña y sesión de servidor.
- Resolución **Personas y Enrolamiento Biométrico** (PROVISIONAL — ADOPTADA): registro administrativo separado del enrolamiento; 0007-A cubre solo el primero.
- Resolución **Registro de Personas y Persistencia MySQL** (PROVISIONAL): campos mínimos, identificador institucional obligatorio para ESTUDIANTE, TipoPersona desde catálogo controlado, tipo documental concreto pendiente.
- [`../backend/openapi.json`](../backend/openapi.json), [`../backend/README.md`](../backend/README.md) y el código Flask determinan el contrato implementado. Las guías académicas se consultaron como referencia técnica para semántica, accesibilidad, CSS adaptable, cliente HTTP, manejo de errores y pruebas. Sus ejemplos de JWT, CORS y dominio de alojamientos no se adoptaron.
- Cotejo: el flujo web pasa por React → Flask → aplicación/dominio; React no accede a persistencia. Se respetan los roles provisionales, la autorización efectiva del backend, sesión humana server-side con cookie y CSRF, y la separación entre registro administrativo y enrolamiento. La relación obligatoria de la sección 20 de v1.5 fue sustituida en ese ámbito por la resolución posterior de Identity/IAM; el frontend no presupone un vínculo cuenta–Persona. No se identificó contradicción material dentro de 0007-A.

## Punto de partida y autorización

- Rama `main`, commit `7448590`, árbol limpio antes de crear `frontend/`; no había frontend propio.
- Node.js 22.14.0 y npm 10.9.2 disponibles. Node 24 LTS sigue siendo el baseline provisional. Vite 7.1.12 declara `^20.19.0 || >=22.12.0`; Vitest 3.2.4 y React Router DOM 7.9.4 también aceptan 22.14.0. Build, lint y pruebas se ejecutaron con 22.14.0; Node 24 no se probó localmente.
- Alcance aprobado por el encargo: estructura React/Vite/Bootstrap; autenticación Flask; listado, consulta y registro de Personas; pruebas y documentación. No se autorizan cambios de backend, MySQL, Edge ni Git de escritura.

## Criterios y contrato usados

- `/api/v1/auth/csrf` establece cookie anónima y entrega `csrf_token`; login `POST` exige `X-CSRF-Token`, devuelve identidad `{id_usuario, login, rol}`, rota cookie y entrega CSRF nuevo en cabecera. `/auth/me` recupera sesión; logout `POST` exige CSRF.
- Cookie `recon_session`: `HttpOnly`, `SameSite=Lax`, `Path=/api/v1`, `Secure` salvo excepción HTTP local explícita. Vite usa proxy local de mismo origen; Flask sigue validando host, transporte, sesión, rol y CSRF.
- Personas: solo SUPERADMIN y ADMINISTRADOR. `GET /personas` recibe filtros y paginación; responde `{personas, limite, desplazamiento}` sin total. `GET /personas/tipos` devuelve `{tipos}`. `GET /personas/{id}` devuelve la Persona; `POST /personas` acepta los ocho campos documentados y devuelve 201 con la Persona creada. Error HTTP en `{error}`.
- La interfaz debe distinguir carga, vacío, éxito y error; ser accesible con teclado; usar datos solo de la API; adaptarse a móvil y escritorio. Las pruebas automatizadas usan datos ficticios y no se conectan a MySQL.
- La revisión de contraste corrigió la leyenda lateral a `#506779` sobre blanco (5,90:1) y el foco sobre fondos claros a `#825400` (6,53:1 sobre blanco). En la barra oscura se mantiene el foco `#efb342` (7,11:1 sobre `#123248`). Los demás pares de texto propios del frontend revisados alcanzan al menos 4,5:1; los controles siguen usando estilos Bootstrap.

## Pendientes del alcance

- Validación manual con Flask y MySQL de desarrollo por el responsable, sin operación de base desde esta entrega.
- Validación posterior del flujo de teclado y lector de pantalla con navegador y backend reales por el responsable. La revisión independiente del ZIP fue favorable; esta corrección puntual queda disponible para su comprobación.
- Catálogo definitivo de tipos documentales, reglas especiales de otras categorías, despliegue HTTPS y módulos futuros.
