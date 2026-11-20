# Macro E — ensayo real del código post-D/E

Fecha20/11/2026. Proyecto `recon0010-e-072130`, volumen nuevo y
credenciales nuevas externas. Preflight: identidad/host/cuenta/privilegios y cero
tablas/objetos antes de migrar. CLI oficial aplicó0001–0006 solo allí; bootstrap
ficticio oficial creó una SUPERADMIN y los casos de uso oficiales dos cuentas.
No se accedió a MySQL Windows o Azure. No hay nueva escritura Git.

Resultados:68 pruebas backend focales,12 frontend, Ruff/ESLint/build;4 pruebas de
renderizador Azure. No se repitieron suites históricas completas sin deriva:
comparación AST sin docstrings y cuerpo JS sin encabezado acredita misma lógica.

**Runtime nuevo:**80 comprobaciones HTTPS/API y26 Edge sin API simulada. Cookie
Secure/HttpOnly/SameSite, CSRF, tres roles, cuerpos cerrados/400,401,403,404,409,
PATCH/login normalizado/persistido, credencial y sesión conservadas. Auditoría
de éxito y rollback MySQL al fallar auditoría en proceso auxiliar. Persona,
Punto, metadatos Edge inactivos, eventos manuales/replay/incidencia y proyección
reducida. UI guardó otro login por formulario real, mostró conflicto409 y
respetó Eliminar Persona deshabilitado. Desktop/móvil y foco de ojo comprobados.

Parada controlada de DB propia devolvió503 genérico. Reinicio completo sin build,
migración o bootstrap conservó todos los conteos y huellas públicas, y permitió
login con identificador editado. Hashes del frontend en servicio coincidieron
con artefactos compilados;81 módulos backend y fuentes de migración/WSGI se
verificaron en imagen. Compose local, locks, revisiones y configuración de
seguridad conservan sus bytes previos. El proyecto se apagó sin-v; todos los
volúmenes anteriores y el nuevo se conservaron. Sesiones autenticadas activas:0.

Conteos finales reales: `{"usuario_plataforma": 3, "persona": 1, "punto_acceso": 1, "dispositivo_edge": 1, "evento_acceso": 3, "auditoria_iam": 5, "auditoria_personas": 2, "evento_auditoria": 6, "sesion_usuario": 20}`.

La construcción usó recetas externas offline equivalentes: backend desde imagen
local de dependencias ya verificadas con COPY de TODAS las fuentes actuales;
frontend compilado offline y copiado en Nginx limpio por digest. No se ejecutó
pip/npm install ni se descargaron capas. Un primer FROM expresado como ID fue
interpretado como nombre remoto y falló consultando metadatos; se corrigió el
auxiliar a etiqueta local verificada. No se acredita reconstrucción fría con
instalación, ni auditoría nueva online de dependencias.

TLS fue autofirmado local, confiado solo por el cliente de prueba/SPKI de Edge;
no se modificó confianza global. La variante Azure pasó Compose config y
nginx-t con nombre/certificado sintéticos: **NO Azure real**. Zoom200% humano,
G6 Windows1045, C15/D08/D09/D13, retención/eliminación y reservas dev anteriores
siguen pendientes. Incremento0010 ABIERTO; revisión independiente antes de Git.
