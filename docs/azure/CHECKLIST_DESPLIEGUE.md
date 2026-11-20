# Checklist de transferencia Azure — no ejecutado por Macro C

Fuente de infraestructura: informe aportado20/11/2026, no consultado en vivo.
Contrato canónico: [VIGENTE](./CONTRATO_DESPLIEGUE.md).

| Puerta | Comprobación y criterio antes de avanzar |
|---|---|
| Ventana/costos | Responsable verifica VM, saldo y horario10:00–11:30 Bogotá; primera ejecución automática no acreditada. Ajustar con permiso antes de grabar/evaluar |
|19 versión | Usar SHA remoto real del acta externa C5; Deploy Key lectura. Inspeccionar /home/azureuser/recon-platform/source vacío/propietario/permisos antes de clonar. STOP si existe otro árbol o SHA distinto |
|19 código | Monorepo backend/frontend Vanilla; comprobar git rev-parse HEAD y status sin deriva; revisar Dockerfiles/Compose/lock desde ese mismo SHA |
|20 DB | Proyecto/volumen/base NUEVOS; secretos NUEVOS y privados Ubuntu. Nombres lógicos del adaptador son fijos; no Windows ni volumen del laboratorio. Identidad/privilegios/vacío antes de upgrade; backup si ya hay datos |
|21 backend | Build Linux, WSGI, CLI *_FILE explícita; seis revisiones separadas del arranque; bootstrap oficial con prompts ocultos. Liveness no es readiness de esquema/login |
|22 frontend | npm ci/build en builder; Nginx solo estáticos, fallback SPA y /api/v1 mismo origen. Nunca React o servidor Vite público |
|23 TLS/red | Adaptación FQDN/Host/TLS pública y proxy confiable revisada antes de exponer login.443 al proxy;80 solo ACME/redirect implementados; no8080/3306/8000/5000/socket Docker públicos |
|23 E2E | DNS/HTTPS reales, cookies/CSRF,3 roles, formularios, Network/API,4xx previstos,5xx controlados sin SQL/secretos, persistencia y conciliación |
| Video | Verificación humana200%/D12 aparte; no passwords/cookies/tokens en pantalla. Portal/SSH/Docker/Git SHA/Network/costos y funciones reales; Anexo B excluido |
| Fin | Revisar disponibilidad durante evaluación y luego detener/desasignar según autorización; presupuesto no apaga recursos, disco/IP/automatización pueden seguir costando |

Datos documentales de coordinación: rg-recon-platform-g01, vm-recon-platform-g01,
FQDN recon-platform-g01.northcentralus.cloudapp.azure.com. VM2vCPU/4GiB/disco32GiB;
Docker Engine29.10.0/Compose5.8.0 reportados. Usar sudo docker según la preparación
existente; no cambiar grupos o NSG por leer este checklist. No almacenar claves
privadas ni datos de SSH en el repo. No se ejecutó clone/cloud build/up/DDL/NSG/TLS.

Pasos1–18 de infraestructura reportados con reservas de automatización;19 falta
clon estable;20–23 siguen pendientes hasta comprobación real. Confirmar minuto
de entrega en aula (se comunicó21/11/2026 antes23:59; no es evidencia del aula).
G6 Windows, cuatro reservas, D12, deuda dev y eliminación Persona permanecen.
Incremento0010 ABIERTO; despliegue público y cierre exigen revisión separada.
