# Frontend Recon Facial — SPA Vanilla

Incremento 0010, Macrobloque D, promoción G5 autorizada el 19/11/2026. La entrada principal es [index.html](./index.html) → [main.js](./src/main.js). Vite es herramienta de desarrollo/build; no hay React como UI de esta aplicación. Bootstrap se importa localmente.

## Ejecución y verificaciones

**Estado actual: candidata local, Macro C; Incremento 0010 abierto.**
El ensayo Docker aprobado pasó 190/190 Vitest (incluye regresión de foco nativo),
ESLint/build, HTTPS y Edge. Lock: Vite 7.3.8/Vitest 3.2.7; Node 26.13.1 en Docker.
Son pruebas históricas reutilizables por hash; no certifican Azure o zoom humano.
[Ensayo y límites](../docs/pruebas/DOCKER_LOCAL_0010.md),
[contrato Azure](../docs/azure/CONTRATO_DESPLIEGUE.md).
La instalación Windows anterior no se actualizó; probar el nuevo lock solo en
un entorno coherente. Audit producción sin avisos, tres paquetes dev con deuda.

### Corte histórico Macro A — conservado

189/189 Vitest (12 casos nuevos), ESLint y build satisfactorios. Se verificó el
grafo productivo de 44 módulos sin React ni legado. El
[índice](../docs/README.md) y la [guía actual](../docs/pruebas/ESTABILIZACION_A.md)
describen el alcance. G6 no se ejecutó en A; la reanudación anterior E0 quedó
detenida antes de importar hijos, con 0/1 del nuevo cupo de clave consumido.
Se conservan los permisos condicionados y las reservas para la siguiente puerta.

Desde esta carpeta, los scripts portables son `npm test`, `npm run lint` y
`npm run build`, sobre instalación ya existente. Node 26 requiere en el ensayo
`--no-experimental-webstorage`. La reproducción exacta aislada usa los auxiliares
externos del ZIP actual; no depende de una ruta antigua en Descargas. No instala
paquetes, consulta credenciales o inicia servicios por comprobar estas órdenes.

### Antecedente G5 y comandos históricos

Los comandos externos siguientes documentan el ensayo G5 y pueden referirse a
carpetas que ya no existen. No son la guía actual ni deben ejecutarse literalmente.

G5 pasó 177/177 Vitest, ESLint y build; backend focal: 78 pruebas únicas satisfactorias (77 iniciales + una focal tras corrección del auxiliar). G6: C0 APTO, pero arranque API bloqueado por auxiliar Popen antes de disponibilidad; preview/browser/smoke no ejecutados. Se consumió una clave efímera; sin reintento. Resultados y límites en la entrega externa. El incremento permanece ABIERTO, sujeto a revisión independiente. C15/D08/D09/D13 siguen abiertos; D12 conserva constatación humana del zoom pendiente.

Herramientas locales ya verificadas, sin instalar ni acceder a red. Desde esta carpeta, bajo el controlador externo y sus guardias:

```powershell
& 'C:/Program Files/nodejs/node.exe' './node_modules/vitest/vitest.mjs' run --config 'C:/Users/casa/Downloads/RECON_G5_G6_EJECUCION_20261119_172819/AUX/vitest.g5.config.mjs'
& 'C:/Program Files/nodejs/node.exe' './node_modules/eslint/bin/eslint.js' --config './eslint.config.js' .
& 'C:/Program Files/nodejs/node.exe' './node_modules/vite/bin/vite.js' build --config './vite.config.js'
# Preview únicamente después de verificaciones, con permiso local vigente:
& 'C:/Program Files/nodejs/node.exe' './node_modules/vite/bin/vite.js' preview --config './vite.config.js' --host 127.0.0.1 --port 5173 --strictPort
```

Las órdenes son las llamadas hijas del runner autorizado y requieren su entorno aislado: sin carga .env, sin red externa, sin autofix. La configuración auxiliar Vitest importa la configuración de esta raíz y solo fija loopback, hmr:false, api:false y watch:false; no cambia selección, pruebas, setup ni tiempos. El runner conserva preload en workers y la corrección WebStorage para Node 26. Test → lint → build es secuencial y condicionado; no ejecutar las órdenes solas ni juntas ignorando un fallo. Los argumentos y variables no secretos realmente usados constan en la guía reproducible de la entrega externa. Las dependencias provienen de copia local verificada, no de una instalación nueva.

Flask se configura por controlador privado con pruebas=True, destino exclusivo recon_tests y puerto5000. No usar comandos genéricos que seleccionen desarrollo. Preview5173 sirve dist y proxy /api/v1; no es despliegue de producción. Las credenciales nunca van en archivos ni argumentos.

React anterior y candidata se conservan localmente, ignorados y fuera de la publicación:
[tratamiento de respaldos](../docs/arquitectura/README.md#respaldos-locales-no-publicados).
README/DESIGN originales permanecen en el legado local. Los documentos históricos
conservan su etapa. No borrar esos árboles ni operar Git sin autorización independiente.
