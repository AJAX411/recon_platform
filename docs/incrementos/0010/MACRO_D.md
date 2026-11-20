# Incremento 0010 — Macroencargo D, candidata para revisión

Estado: ABIERTO. Baseline v1.7 con resoluciones puntuales aprobadas, ADR-D0-BE-01 y SPA Vanilla. No se aplican cambios de esquema ni migraciones. No se publica commit desde esta entrega.

- Login institucional de dos paneles, responsive y ojo inline accesible. Autenticación, cookie y CSRF conservados.
- Jornada sin sufijo decorativo en cabecera, zona America/Bogota intacta. Eliminación de Persona bloqueada con ayuda breve y distinción de baja lógica.
- Editar usuario modifica únicamente login de cuenta administrable mediante `PATCH /api/v1/iam/usuarios/{usuario_id}/login`. Solo SUPERADMIN activo, con CSRF; cuenta SUPERADMIN inicial protegida; auditoría y rollback del caso de uso existente. Sin columnas nuevas ni vínculo Persona. Cambiar rol/estado permanecen separados, sin guardados parciales conjuntos.
- Backend mantiene módulos canónicos planos por capacidad según ADR. No se trasladan módulos por apariencia de carpetas antiguas; cachés y entornos se conservan.
- Históricos centralizados por número bajo este árbol, conservando contenido y corrigiendo enlaces relativos.

La evidencia nueva de unitarias, lint, build y navegador con API ficticia se entrega externamente. No acredita integración MySQL real del nuevo PATCH ni sustituye la revisión visual humana de zoom 200 %. Los 190/20/87/37 históricos pertenecen al corte Docker anterior, no al runtime modificado.

Antes de desplegar: revisión independiente, autorización de publicación, nuevo SHA real, reconstrucción de frontend y backend y humo HTTPS/IAM con base de ensayo autorizada. No usar el SHA previo para atribuirle estos ajustes. Azure y MySQL Windows no se acceden aquí; G6 Windows 1045, C15/D08/D09/D13, D12 humana y reservas de dependencias siguen abiertas.
