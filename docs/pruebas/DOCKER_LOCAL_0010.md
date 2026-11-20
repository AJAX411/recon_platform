# Validación Docker local — Incremento 0010

> Corte histórico anterior a Macro D/E. La verificación actualizada se documenta en [Macro E](./MACRO_E_DOCKER.md); los resultados siguientes conservan su fecha y alcance originales.

20/11/2026. **LISTO PARA REVISIÓN DE ESTABILIDAD LOCAL**, con reservas. No cierra
Incremento0010 ni G6 Windows. [Compose](../../compose.yaml),
[guía Docker](../../deploy/README.md) y
[contrato Azure](../azure/CONTRATO_DESPLIEGUE.md).

## Resultados nuevos

- Bases oficiales linux/amd64 por digest, Python3.14.10/Node26.13.1/Nginx1.30.7.
- Gunicorn25.3.0, imports/wheels y procesos no root comprobados; Flask/ORM intactos.
- Frontend190/190 Vitest (189 conservadas más regresión del traslado nativo de foco
  al botón Perfil), ESLint/build y grafo43 sin React/JSX/legado/candidata.
- Adaptador20/20, incluyendo CLI *_FILE antes de factory y rechazo de destinos;
  Ruff. Validación Compose estructural y real, nginx -t y healthchecks.
- HTTPS/API87 controles; Edge37 controles; cookies HttpOnly/Secure/SameSite,
  CSRF, RBAC3roles, errores400/401/403/404/409 y 503 controlado al detener DB propia.
- Cinco Personas ficticias (cuatro API, quinta formulario real), dos Puntos,
  un Edge administrativo inactivo sin comunicación, cinco eventos manuales y dos
  incidencias. Sin imágenes, embeddings, enrolamiento ni autorización física.
- Seis migraciones existentes solo DB Docker nueva, revisión0006_evento_acceso,
  doce tablas. Bootstrap oficial de una SUPERADMIN; otras cuentas por caso de uso.
- Parada/reinicio de servicios propios sin pull/build/migración: conteos, quinto
  registro, revisión y login HTTPS persistieron. Down final sin -v; volumen guardado.

Las suites se repitieron solo por cambio de lock/foco y fallos de auxiliares de
captura documentados en el ZIP; no se repitió G5 ni integración Windows.
El foco se corrigió consultando relatedTarget antes de ocultar el menú: Edge
presentaba BODY temporalmente como activeElement y anulaba el click de Perfil.

## Seguridad y límites

Audit --omit=dev: cero avisos. Audit completo: @vitest/mocker moderado, tinypool
crítico y vitest crítico por dependencias. No se usó audit fix --force ni una
actualización mayor indiscriminada. Pruebas en Docker sin red/secretos, sin API/UI
Vitest y sin opciones/worker remotos; runtime Nginx solo estáticos, sin Node/npm
o node_modules. Deuda dev pendiente de aprobación humana, no producción certificada.
No se verificaron firmas/SBOM ni todos los CVE de capas OS. Pip fija versiones
y usa wheels oficiales, pero no un lock --require-hashes de todos los binarios.

HTTPS solo loopback8443. API/DB sin publicación. Web/data internas; entrada_local
solo Nginx, binding127.0.0.1 y masqueradefalse. No equivale a firewall de egress
auditado para producción. TLS autofirmado7d, confianza local acotada, sin cambios
globales de certificados. Secretos nuevos fuera del repositorio e imágenes/ZIP.

El historial OPERADOR tuvo cinco filas reales con tres columnas reducidas,
sin Persona/IDs/detalles. El atajo Ctrl+Equal en Edge headless no cambió DPR ni
viewport; zoom200% **NO VERIFICADO**, no se sustituyó con CSS/emulación. D12 humana
y cuatro reservas C15/D08/D09/D13 siguen pendientes de revisión, sin cierre global.
G6 Windows continúa bloqueado: no conexiones ni C0 nuevos, sin ALTER/GRANT.

## Reanudación local tras revisión

El ZIP externo incluye rutas concretas del proyecto/archivo de rutas privado,
digests, comandos reproducibles, visor privado opcional y lista de demostración.
Usar siempre --project-name y --env-file explícitos, imágenes propias, --pull never
y --no-build para reabrir este volumen. No volver a migrar, hacer bootstrap o
sembrar fixtures por rutina. No usar down -v, prune ni recursos ajenos.
Para una base realmente nueva, verificar primero identidad/vacío y usar el CLI
app_wsgi:create_cli_app con secretos montados; las seis revisiones y el bootstrap
requieren sus controles. No aplicar comandos de contenedor a bases Windows.
