# Arquitectura frontend — promoción Vanilla G5

[main](./src/main.js) importa Bootstrap y estilos, construye [app](./src/app.js), router History y páginas/componentes DOM nativos. [routes](./src/routes.js) mantiene 19 rutas y fallback; [sessionStore](./src/auth/sessionStore.js) gestiona estado/épocas; [http](./src/api/http.js) centraliza /api/v1, cookies, CSRF y errores. El backend conserva autenticación/autorización y contratos.

Persona ≠ UsuarioPlataforma. Rol O mantiene proyección reducida; guards UI no sustituyen permisos backend. No JWT en localStorage ni imágenes/biometría simuladas. Registrar un Dispositivo Edge no acredita integración física.

React original, dependencias y dist anteriores se preservan en legacy-react/INC0010_G5_20261119_172819; la ID efectiva consta en el diario externo. La candidata permanece independiente. Vite raíz aplica envDir:false, loopback5173 estricto y proxy5000, genera inventario productivo de módulos. ESLint ignora solo árboles inactivos y salidas; Vitest descubre tests/**/*.check.js.

Manifiesto y lock nativos G2-A se adoptan por SHA-256. react-is es dependencia transitiva de herramientas de desarrollo, ajena al grafo productivo permitido. No regenerar lock para eliminar coincidencias textuales.

La evidencia de validación e integración de esta raíz se entrega fuera del repositorio. No se declara cierre ni resolución de C15/D08/D09/D13 o D12 humano. El diseño anterior se conserva en el DESIGN del legado; no se borra la cronología.

## Macro D — login y acciones

Login institucional 46/54 en escritorio, apilado hasta 900 px, sin altura fija móvil. Ojo SVG local dentro del campo, etiqueta dinámica y foco conservado. Colores marino/teal, secundarios con borde, Desactivar ámbar y Eliminar deshabilitado rojo tenue. Editar usuario envía solo login a la API; Cambiar rol y estado siguen independientes y confirmados. No cambia el reloj America/Bogota.
