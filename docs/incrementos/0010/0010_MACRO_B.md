# Incremento 0010 — Macro B para revisión independiente

Dos carriles autorizados: B1 G6 con gates; B2 archivos y validación estática
Docker. Sin autorización B2-RUN-LOCAL, instalaciones/descargas, inicialización,
migraciones, Git de escritura, Azure o Macro C. Incremento ABIERTO.

## B1

El baseline A coincide: 375 fuentes y cuatro dist; se reutilizan 189/189,
lint/build de A y pruebas anteriores válidas. No se repitió G5 o su promoción.

E0 pasó en hijos reales, Popen nativo/audit veto, asyncio Windows, factory
inerte, preview/browser sin servicios, guardias, UTF-8 y hashes. Se ampliaron
los auxiliares externos para cubrir Perfil, nuevos resúmenes de Persona sin
POST/PATCH, navegación SPA y selector Edge. Se validó su delta sin secretos.

El lector externo mínimo requirió una corrección de formato antes de conectar;
se probó con tres fixtures ficticias. Luego hubo **un único intento de conexión
MySQL**, rechazado con código 1045 antes de SELECT. No se confirmó identidad ni
esquema, no se generó SECRET_KEY, no se iniciaron API/preview/browser ni sesiones.
Se detuvo B1 sin probar credenciales alternativas, GRANT, bootstrap o cambios de
cuenta. El error por sí solo no prueba una causa única. Reanudar requiere revisión
del canal/cuenta/destino y una instrucción posterior al STOP, no ensayo repetitivo.

La clave nueva sigue sin consumo, 0/1. G6 real no aprobado. No hubo lecturas de
datos de negocio ni conciliación MySQL posible. C15/D08/D09/D13 y D12 humano
permanecen abiertos, así como política de anonimización de Persona.

## B2

Se crearon Dockerfiles y whitelists por contexto raíz, dependencias de runtime
fijadas desde metadatos locales, propuesta WSGI Linux, Nginx HTTPS, Compose
con tres servicios aislados, plantilla de rutas privadas y verificador estático.
No se modificó código de aplicación backend/frontend ni OpenAPI/locks/migraciones.

17 tests nuevos del adaptador PASS; Ruff PASS; diez propiedades estructurales
y Compose config --quiet PASS con fixtures inertes externas. No se instalan
dependencias para probar esto. No hay motor Linux disponible ni imágenes
confirmadas; no se ejecutó hadolint/nginx -t, build, up, TLS o E2E Docker.

La [guía Docker](../../../deploy/README.md) y el
[contrato de despliegue](../../azure/CONTRATO_DESPLIEGUE.md) detallan arquitectura,
separación de secretos/gates, imágenes/digests pendientes, procedimientos de
inicialización/migraciones y cierre sin borrar volumen. Preparación estática
no equivale a contenedores reproducidos o versión demostrable E2E.

Se conserva React, candidata, backend, datos existentes y cambios anteriores.
Se entrega un ZIP externo con matrices, fuentes/diffs, informes y evidencias;
la revisión independiente decide el siguiente paso, sin iniciar Macro C.
