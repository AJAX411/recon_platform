# Validación de Macro A y reproducción

## Resultados de esta entrega

| Comprobación | Resultado real |
|---|---|
| Vitest focal nuevo | 12/12 PASS, un archivo |
| Vitest completo tras cambios de aplicación | 189/189 PASS, seis archivos: 65 + 41 + 41 + 25 + 12 + 5 |
| ESLint raíz Vanilla | PASS, sin errores ni avisos |
| Vite build raíz | PASS, 44 módulos; sin React, JSX, candidata o legado en grafo |
| Auditoría AST backend | Cuatro controles PASS; 81 módulos, imports, dominios, dependencias/transacciones y contrato/migraciones intactos |
| Factory/contrato aislados | PASS: ocho blueprints, 35 operaciones OpenAPI, once tablas ORM; cero conexiones |
| Ruff backend | PASS, selección E4/E7/E9/F, sin cache ni autofix |
| MySQL, HTTP sobre red, browser autenticado, zoom/Narrador humanos | NO EJECUTADOS en A |

La suite backend histórica y las verificaciones de instalación válidas se
reutilizan; no se ejecutó una nueva suite backend completa. Los cambios de A
no alteran su código, modelos, migraciones ni OpenAPI. La comprobación nueva de
factory utiliza URI SQLite inerte y veta conexiones antes del registro de
modelos; el diagnóstico usa test_client, sin servidor TCP ni SECRET_KEY real.

La repetición completa de Vitest se justifica por cambios compartidos en
confirmación/estado/ciclo DOM. Los doce focales aparecen también en la suite
completa: **189 casos únicos**, no 201. Se mantienen las 177 pruebas anteriores,
con adaptación de expectativas Perfil/confirmaciones/selector Edge al contrato
docente. No se eliminaron suites ni se relajaron guardias para hacerlas pasar.

## Comandos disponibles en el proyecto

Desde frontend, con entorno aprobado y dependencias ya presentes, los scripts
son `npm test`, `npm run lint` y `npm run build`. En Node 26 las comprobaciones
usaron `--no-experimental-webstorage`, heredado por los procesos de Vitest.
No instalar ni modificar el lock para ejecutar estos scripts. No usar el texto
anterior como autorización para conectar servicios reales.

La ejecución exacta de A utiliza auxiliares **externos** incluidos en el ZIP:
importa las configuraciones nativas, fija `config:false`/`configFile:false`,
cacheDir externo, setup original, JSDOM, forks de un trabajador y preloads
heredados. Veta sockets, listeners y DNS externo; resuelve loopback de forma
sintética. Rechaza sin proceso la consulta opcional `net use` de Vite Windows.
Vitest escribió además un `results.json` en su caché ignorada dentro de
`frontend/node_modules/.vite/vitest/`; se conserva y se identifica en el postflight.
Los 4.648 archivos preexistentes de instalación mantienen sus hashes. Este
archivo de resultados generado no es una instalación ni una edición de paquete.
No usa claves o credenciales del documento privado. Los comandos exactos,
hashes, stdout/stderr y fallos auxiliares acotados constan en el paquete.

Ruff, desde backend, tal como se ejecutó:

```powershell
& '.\.venv\Scripts\ruff.exe' check --isolated --no-cache --no-fix --select E4,E7,E9,F src tests scripts
```

## Límites y puertas posteriores

JSDOM comprueba DOM, foco simulado, navegación, contratos mediante dobles y
ausencia de POST duplicado. No acredita top layer nativo, inercia del navegador,
zoom real 200 %, Narrador ni transporte/cookies en integración real. La matriz
de tres roles UI tampoco sustituye RBAC backend sobre MySQL.

Macro B necesita revisión A, versión exacta sin deriva, E0 completo, C0 y gates
de datos/servicios/clave vigentes. No se corrieron pruebas MySQL ni migraciones
desde esta guía. C15/D08/D09/D13 y D12 humano permanecen pendientes.
