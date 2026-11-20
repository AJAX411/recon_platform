# Guía de sustentación — recorrido de 8–10 minutos

El estudiante explica lo que existe y las pruebas que realmente se ejecutaron.
Incremento0010 sigue abierto; esta guía no acredita Azure, biometría física ni
zoom humano200%. [Mapa completo](./GUIA_LECTURA_CODIGO.md).

| Tiempo | Archivo que mostrar en VS Code | Explicación y demostración |
|---|---|---|
|0:00–0:45| [README](../../README.md), [arquitectura](./README.md) | Objetivo administrativo, seis capacidades; Persona y cuenta independientes; límites biométricos |
|0:45–2:00| [main](../../frontend/src/main.js), [app](../../frontend/src/app.js), [router](../../frontend/src/router.js), [routes](../../frontend/src/routes.js) | SPA nativa: una entrada, History API, montaje/limpieza DOM; Vite desarrolla/compila, no es servidor público |
|2:00–3:15| [LoginPage](../../frontend/src/pages/LoginPage.js), [sessionStore](../../frontend/src/auth/sessionStore.js), [http](../../frontend/src/api/http.js) | Render dinámico, evento submit, await, cookie y CSRF; mostrar ojo/foco sin exponer una contraseña |
|3:15–4:30| [factory](../../backend/src/recon_platform/__init__.py), [seguridad_http](../../backend/src/recon_platform/identidad/seguridad_http.py), [controlador_usuarios](../../backend/src/recon_platform/identidad/controlador_usuarios.py) | app factory, blueprints, API REST/JSON, RBAC backend, cuerpo exacto y códigos |
|4:30–5:45| [servicio_cuentas](../../backend/src/recon_platform/identidad/servicio_cuentas.py), [contratos](../../backend/src/recon_platform/identidad/contratos_cuentas.py), [repositorio](../../backend/src/recon_platform/identidad/repositorio_cuentas.py), [modelos](../../backend/src/recon_platform/identidad/modelos.py) | Editar login conserva contrato; entidad distinta del ORM; puerto inyectado y auditoría atómica; no borrar SUPERADMIN |
|5:45–6:45| [servicio_eventos](../../backend/src/recon_platform/accesos/servicio_eventos.py), [evento_acceso](../../backend/src/recon_platform/accesos/evento_acceso.py) | Idempotencia, bloqueo, UTC/Bogotá, commit/rollback; declaración humana no acciona hardware |
|6:45–8:00| [Compose](../../compose.yaml), [Dockerfiles](../../frontend/Dockerfile), [app_wsgi](../../backend/deploy/app_wsgi.py), [guía Docker](../../deploy/README.md) | Nginx→Gunicorn→MySQL nuevo, redes/puertos, secretos por archivos; liveness distinto de readiness; volumen persiste |
|8:00–9:00| [OpenAPI](../../backend/openapi.json), [guía de pruebas](../pruebas/DOCKER_LOCAL_0010.md), [contrato Azure](../azure/CONTRATO_DESPLIEGUE.md) |36 operaciones, evidencia nueva frente a histórica, revisión independiente, SHA futuro; Azure todavía no desplegado |

## Preguntas y respuestas concretas

**¿Por qué Vanilla si antes había React?** La resolución posterior aprobó una
SPA nativa; el respaldo React se conserva fuera del runtime. Componentes son
funciones DOM reutilizables, páginas montan/limpian y el router conserva navegación.
No se afirma que Vanilla sea obligatorio para todo proyecto.

**¿Dónde están las capas si los archivos están juntos?** En responsabilidades:
controlador HTTP, DTO, servicio, entidad, Protocol, repositorio/ORM y unidad de
trabajo. ADR-D0-BE-01 evita carpetas de una sola pieza sin mezclar reglas con Flask.

**¿SQLAlchemy evita validar?** No. Dominio/servicio validan reglas y permisos;
MySQL agrega FK/UNIQUE/CHECK. El repositorio traduce integridad; la transacción
del caso de uso revierte tanto cambio como auditoría si algo falla.

**¿Para qué migraciones?** Versionan cambios de esquema revisados; no corren al
arrancar. En este encargo solo se autorizan las seis existentes dentro de una
base Docker nueva cuya identidad/vacío se haya verificado; nunca Windows.

**¿Cómo protege autenticación?** scrypt para credenciales, token opaco con digest
persistido, cookie HttpOnly/Secure/SameSite, CSRF en mutaciones y rol actual en el
servidor. Guard UI ayuda a navegar; no concede autorización. No mostrar secretos.

**¿Editar usuario cambia también rol o contraseña?** No: PATCH/login admite solo
login. Rol/estado son operaciones separadas con confirmación. La SUPERADMIN inicial
está protegida; no hay FK con Persona ni campos personales inventados.

**¿Por qué Eliminar no funciona?** Requiere política aprobada de supresión y
anonimización. Desactivar conserva el registro; no se lo presenta como borrado.

**¿Qué verifica Docker?** La versión local construida y el ensayo real registrado,
con base ficticia nueva y HTTPS loopback. No prueba DNS/NSG/TLS público de Azure;
una configuración preparada tampoco equivale a despliegue comprobado.

**¿Hay reconocimiento facial integrado?** No. Edge aquí administra metadatos.
Detector/embedder, ONNX–HEF y pruebas físicas siguen en investigación/PoC por ámbito.

**¿Qué falta para publicar y cerrar?** Revisión independiente visual/técnica,
autorización separada Git y SHA real; después autorización y comprobación Azure.
El zoom200% humano y las reservas documentadas no se dan por aprobados por la guía.

Antes de grabar, ocultar archivos privados, .env, variables de proceso, cookies,
tokens y contraseñas. Usar cuentas/datos ficticios del ensayo autorizado. Mostrar
sumarios de resultados, nunca dumps o el panel Application con cookies de sesión.
