# ADR-D0-BE-01 — Organización proporcional por capacidades

**Decisión:** aprobada expresamente por el responsable el 18/11/2026 para el
Macrobloque C. Implementación local sujeta a revisión independiente. No cierra
el Incremento 0010 ni autoriza el Macrobloque D.

## Problema y refinamiento

La estructura 0009 separa correctamente responsabilidades, pero sus carpetas
de una sola pieza dificultan recorrer el código durante la sustentación.
Se conserva el monolito modular y se ubican los archivos directamente dentro
de cada una de sus seis capacidades. Esta decisión refina ubicación e imports
de 0009; no publica una nueva versión del Contexto Maestro v1.7 OFICIAL.

Personas fue el piloto C1. Su extensión C2 está condicionada a pruebas aisladas,
comparación HTTP/ORM, imports y seguridad satisfactorios, registradas fuera
del repositorio. El orden conservador es Consultas → Auditoría → Integración
Edge → Identidad → Accesos, después de Personas.

## Responsabilidades conservadas

| Archivo por responsabilidad | Función |
|---|---|
| controlador, controlador_auth/usuarios/puntos/eventos | HTTP, guards, códigos y cabeceras |
| dto, dto_auth/usuarios/puntos/eventos | Forma de entrada y proyección de salida |
| servicio, servicio_cuentas/sesiones/puntos/eventos | Casos de uso y transacción |
| persona, tipo_persona, rol, sesion, evento_acceso, etc. | Entidades y reglas |
| contratos, contratos_cuentas/sesiones/puntos/eventos/consultas | Protocols de persistencia y colaboración |
| modelos, modelos_puntos/eventos | Única definición ORM canónica por tabla |
| repositorio, repositorio_cuentas/sesiones/puntos/eventos | SQL, hidratación y traducción de integridad |
| unidad_trabajo, unidad_trabajo_eventos, unidad_lectura | Commit/rollback o snapshot de lectura |
| lecturas | Adaptadores de consultas públicas de Personas y Accesos |

Los contratos de consultas de Personas se mantienen separados de persistencia.
IAM conserva contratos de cuentas y sesiones; Accesos conserva contratos de
Puntos, Eventos y Consultas. No se fusionan clases llamadas UnidadTrabajo o
Auditoria por coincidencia nominal: Evento exige iniciar y otros contratos no.
No se introducen fachadas de compatibilidad ni copias de modelos/Blueprints.

Los servicios dependen de dominio y contratos. [Composición](./src/recon_platform/composicion.py)
construye adaptadores con la misma sesión; los repositorios hacen flush cuando
corresponde y el caso de uso decide confirmar/revertir. Los adaptadores siguen
usando modelos de otras capacidades en joins/bloqueos preexistentes. Consultas
colabora por contratos públicos, sin tabla propia ni repositorios ajenos.
Se conserva el helper compartido [HTTP administrativo](./src/recon_platform/http/administrativo.py).

## Consecuencias y límites

Se actualizan consumidores, imports perezosos, monkeypatches, composición,
registro de modelos y únicamente los imports de [env Alembic](./migrations/env.py).
No se ejecuta este entorno: su cuerpo selecciona y ejecuta migraciones aunque
su docstring histórico afirme otra cosa. Las seis revisiones son inmutables.
Los inicializadores retirados solo contenían documentación del paquete antiguo;
los inicializadores de cada capacidad permanecen.

Los tests de estructura reconocen ahora archivos por responsabilidad, conservan
las firmas históricas de DDL/rutas y siguen comprobando ausencia de frameworks
en el núcleo, commits en repositorios, imports rotos y duplicación ORM. Los
demás tests cambian exclusivamente imports/cadenas de monkeypatch.

No cambian OpenAPI, endpoints, cuerpos, permisos, cookies/CSRF, hash scrypt,
bootstrap explícito, transacciones, auditoría, idempotencia o reglas de Persona.
Persona sigue separada de UsuarioPlataforma. ACTIVO no acredita enrolamiento.
Integración Edge sigue administrando metadatos; no integra Raspberry, Hailo,
imágenes, plantillas o hardware. Supresión y decisiones biométricas pendientes
no se resuelven aquí.

No se reinstalan paquetes ni se actualizan metadatos egg-info históricos. La
instalación editable sigue apuntando a src; sus listas de fuentes pueden reflejar
el árbol anterior hasta una operación de empaquetado autorizada. No son otro
módulo de negocio y no deben editarse manualmente para simular una instalación.

React y la candidata Vanilla conservan sus bytes y contratos; React continúa
como entrada vigente. Las pruebas aisladas SQLite/test_client no certifican
MySQL, locks reales, HTTP sobre red, despliegue, accesibilidad o E2E. Su validación
operativa, revisión independiente y autorización de D permanecen separadas.
