# Recon Facial — Plataforma web

Prototipo académico para administrar Personas, cuentas web, Puntos de Acceso,
metadatos de Dispositivos Edge y declaraciones manuales de entrada/salida.
El dashboard, historial, incidencias y auditoría consultan registros de la
plataforma. La presencia mostrada es una estimación del historial, no una
certificación física ni una orden de apertura de puertas.

El frontend operativo es una **SPA nativa con JavaScript Vanilla**, HTML y CSS,
Bootstrap local y Vite para desarrollo/build. El backend es un monolito Flask
modular por seis dominios, con SQLAlchemy y persistencia MySQL. Persona y cuenta
UsuarioPlataforma son entidades independientes. No hay reconocimiento facial,
enrolamiento por foto ni hardware Edge integrado en esta aplicación web.

## Estado y documentación

Incremento 0010 **ABIERTO**. G5 y la estabilización previa conservan sus aprobaciones
y salvedades. El ensayo Docker local aislado funcionó con HTTPS, tres roles,
formularios y persistencia de datos ficticios; quedó apagado conservando volumen.
G6 sobre MySQL Windows sigue pendiente por autenticación, sin nuevos intentos.
C15/D08/D09/D13 y D12 humana continúan abiertos. Macro C prepara esta candidata y
su publicación privada; Azure no se ha ejecutado desde este repositorio.
[Resultados Docker y límites](./docs/pruebas/DOCKER_LOCAL_0010.md).

- [Índice documental](./docs/README.md): fuentes vigentes e historia por ámbito.
- [Arquitectura y dominios](./docs/arquitectura/README.md).
- [Alcance y pendientes de estabilización A](./docs/incrementos/0010_ESTABILIZACION_A.md).
- [Validación y límites](./docs/pruebas/ESTABILIZACION_A.md).
- [Contrato para preparar despliegue](./docs/azure/CONTRATO_DESPLIEGUE.md).
- [Contrato HTTP OpenAPI](./backend/openapi.json).

## Organización

| Ruta | Contenido |
|---|---|
| [backend/src/recon_platform](./backend/src/recon_platform/) | Identidad, Personas, Accesos, Consultas, Auditoría e Integración Edge administrativa |
| [backend/tests](./backend/tests/) | Unitarias aisladas e integración MySQL con activación independiente |
| [backend/migrations](./backend/migrations/) | Revisiones existentes; no se aplican por importar la app |
| [frontend/src](./frontend/src/) | Páginas, componentes DOM, router History, cliente HTTP y estado |
| [frontend/tests](./frontend/tests/) | Vitest/JSDOM, dobles explícitos, sin red real |
| [Respaldo React local](./docs/arquitectura/README.md#respaldos-locales-no-publicados) | Conservado e ignorado; fuera del runtime, build y commit de despliegue |
| [Candidata histórica local](./docs/arquitectura/README.md#respaldos-locales-no-publicados) | Conservada e ignorada; no se presupone en un clon nuevo |
| [docs](./docs/) | Índice y guías actuales, sin mover ni borrar los registros anteriores |

## Preparación y arranque local

Python declarado: 3.14.x; Flask y demás versiones están fijadas en
[pyproject.toml](./backend/pyproject.toml). El ensayo Docker usó Python 3.14.10,
Gunicorn 25.3.0, Node 26.13.1 y Nginx 1.30.7. El entorno Windows anterior con
Python 3.14.7 se conservó; no se confunde con el runtime Linux comprobado.
El lock npm fija versiones. No instalar, regenerar locks o aplicar migraciones
como efecto de una comprobación rutinaria.

El lock actualizado se verificó solo en Docker; las instalaciones Windows se
conservaron sin reinstalación. Para el ensayo vigente consultar la guía Docker.
Con un entorno ya preparado y autorización de ejecución local, el frontend se
inicia desde su carpeta mediante `npm run dev`. Vite limita la interfaz a
loopback:5173 y redirige `/api/v1` a loopback:5000. La navegación usa History API;
los enlaces profundos requieren fallback a la entrada SPA en el servidor web.
No se necesita React ni la candidata para ejecutar la raíz actual.

La vía reproducible del ensayo Linux está en [la guía Docker](./deploy/README.md).
La publicación pública necesita adaptar FQDN/TLS/entrada según el
[contrato Azure](./docs/azure/CONTRATO_DESPLIEGUE.md); el Compose de loopback no
constituye un despliegue Azure. `/_diagnostico` es liveness, no readiness SQL.

La factory real es `recon_platform:create_app`, con parámetro `pruebas` opcional.
La configuración es externa: consultar los nombres de variables en
[config.py](./backend/src/recon_platform/config.py) y la
[plantilla sin secretos](./backend/.env.example). **No arrancar pruebas con un
comando genérico que seleccione desarrollo**. La integración `recon_tests`
requiere su controlador privado, gates y permisos específicos de Macro B.
Los comandos y restricciones se detallan en el
[contrato de ejecución](./docs/azure/CONTRATO_DESPLIEGUE.md).

## Navegación y seguridad

El menú principal contiene Inicio, Personas, Usuarios según rol, Puntos,
Dispositivos, Registro manual e Historial. La campana abre Alertas e incidencias.
El menú del identificador ofrece Perfil de solo lectura y Cerrar sesión.
Los guards de la SPA ayudan a navegar; el backend autoriza cada operación.

Sesiones stateful con cookie opaca HttpOnly, SameSite y Secure por defecto;
CSRF para escrituras. No JWT humano en localStorage ni registro público.
Solo SUPERADMIN administra cuentas/roles; ADMINISTRADOR administra Personas;
OPERADOR conserva consultas reducidas y los permisos operativos específicos
del contrato. No asumir que OPERADOR tiene prohibida toda escritura: el contrato
le permite declaraciones manuales y ciertos cambios de estado/modo.

Desactivar conserva identificadores, datos e historial. **Eliminar datos o
anonimizar Persona está bloqueado** hasta política y contrato aprobados; no se
ha implementado DELETE físico. Las contraseñas, cookies, tokens y datos reales
no pertenecen a informes, capturas, repositorio o entregas ZIP.

## Verificación

Ensayo Docker posterior: 190/190 Vitest, ESLint/build y 20 pruebas del adaptador;
HTTPS, Edge y recuperación reales, con reservas de seguridad/accesibilidad
detalladas en la guía Docker.

Corte histórico Macro A: 189/189 Vitest en seis archivos, ESLint y build satisfactorios; 12 casos
nuevos. La repetición completa se justifica por cambios en componentes y estado.
Backend: verificación focal de imports/estructura, factory sin conexión,
35 operaciones OpenAPI, ocho blueprints y once tablas; Ruff satisfactorio.
Las suites backend históricas válidas se conservan sin repetirlas.

Los comandos reproducibles y la diferencia entre unitarias, integración real,
accesibilidad humana y despliegue están en
[la guía de pruebas](./docs/pruebas/ESTABILIZACION_A.md). No ejecutar integración
MySQL, migraciones, Git de escritura o Azure por seguir este README.
