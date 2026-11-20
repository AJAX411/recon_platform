# Variante Azure — PREPARADA, NO DESPLEGADA

Esta variante se selecciona expresamente con
[compose.azure.yaml](./compose.azure.yaml); el Compose local no la incluye.
Todos los servicios requieren el perfil `approved-azure-runtime`. El bind por
defecto es loopback y el puerto externo previsto es443 hacia Nginx8443. API y
MySQL permanecen internos; nunca publicar5000/8000/3306/8080 ni el socket Docker.
La preparación de archivos no autoriza ejecutar operaciones cloud.

## Qué se conserva y qué cambia

Backend/factory/ORM y las seis revisiones son los canónicos. El adaptador exige
`db:3306/recon_container_0010` y `recon_container_app`: son nombres lógicos que
pueden existir en otro **volumen y proyecto nuevos**, con secretos nuevos.
No apuntar a Windows ni al volumen del laboratorio, ni cambiar esos nombres
mediante env sin revisar el adaptador. Frontend usa `/api/v1` del mismo origen.
No hace falta otra variable VITE de API ni CORS abierto.

La configuración Nginx se renderiza fuera del repositorio y se monta read-only
sobre la configuración local de la imagen. El
[renderizador](./render_nginx.py) valida un FQDN ASCII exacto, rechaza wildcard,
puerto, protocolo e inyección y crea el archivo exclusivamente, sin sobrescribir.
[La plantilla](./nginx.conf.template) exige ese Host, TLS1.2/1.3, certificado/clave
externos, CSP, HSTS, nosniff, DENY y proxy HTTPS acotado al backend. El backend
acepta X-Forwarded-Proto solo del peer frontend; no desactivar cookie Secure.
No se implementa HTTP80/ACME/redirect: ese puerto requiere una solución y permiso
separados. No se genera certificado público ni se instala confianza global.

Los límites iniciales preparados son MySQL1536MiB/1CPU, API512MiB/0.75CPU y
Nginx128MiB/0.25CPU. Suman2176MiB/2CPU, dejando margen al SO en la VM reportada
de4GiB. Son límites de contenedor propuestos, **no capacidad/rendimiento cloud
verificados**; medir y ajustar con autorización. Persistencia y redes mantienen
aislamiento por proyecto. No se ejecutan migraciones ni bootstrap al arrancar.

## Puertas antes de cualquier despliegue

| Paso | Confirmación necesaria en el otro chat |
|---|---|
|19 fuente| Revisión independiente y autorización Git posterior; SHA real publicado que incluya D/E. Clon privado en ruta vacía verificada. El SHA anterior no contiene estos cambios |
|19 imagen| Revisar Dockerfiles/locks/digests del mismo SHA; builds/descargas solo bajo autorización específica de red/recursos. Etiquetas de imágenes revisadas, preferiblemente fijadas por digest al transferir |
|20 datos| Proyecto y volumen Azure nuevos, secretos nuevos, identidad/host/usuario/permisos y esquema vacío antes de las seis migraciones oficiales. No copiar datos/secretos Windows o del laboratorio |
|21 backend| Leer secretos como UID10001, CLI oficial explícita y bootstrap ficticio autorizado. Liveness `/_diagnostico` no sustituye revisión de esquema/login |
|22 frontend| Estáticos compilados, sin Node/Vite público; config renderizada montada, API mismo origen y enlaces profundos SPA |
|23 DNS/TLS| Confirmar FQDN real. El valor reportado es recon-platform-g01.northcentralus.cloudapp.azure.com; no se resolvió ni verificó aquí. Proveer certificado público vigente/cadena/SAN/clave correspondientes |
|23 red| Autorizar bind en interfaz VM o0.0.0.0 y NSG/firewall para443. Default127.0.0.1 no expone el sitio. No abrir puertos de API/DB,8080 o Docker |
|23 pruebas| HTTPS público sin excepciones TLS, cookie/CSRF, tres roles, PATCH login/409/403/400/auditoría, Persona, historial y persistencia. Revisión de recursos/costos y zoom humano200% aparte |

## Preparación reproducible, no ejecutada contra Azure

Copiar [la plantilla de variables](./azure.env.example) a un archivo **externo**
y completar rutas privadas, imágenes revisadas y bind autorizado. No pegar valores
de secretos en argumentos, Git, informes o video. Generar una configuración nueva:

```text
python deploy/azure/render_nginx.py --fqdn FQDN_CONFIRMADO --output RUTA_EXTERNA_NUEVA/nginx.conf
```

Este comando solo renderiza un archivo; no prueba DNS/TLS. Verificar el resultado
y configurar `RECON_AZURE_NGINX_CONFIG_FILE`, rutas TLS y secretos externos. El
renderizador no contiene ni solicita contraseñas. El contrato oficial es
[CONTRATO_DESPLIEGUE](../../docs/azure/CONTRATO_DESPLIEGUE.md).

En Linux hay que comprobar permisos de lectura **con los UID reales de los
contenedores** antes de iniciar: API10001, usuario nginx de la imagen y lector
de secretos del entrypoint MySQL. Los secretos Compose basados en `file` son
montajes; no asumir que campos uid/gid/mode resuelven propiedad/permisos del
archivo fuente. Preparar propietario/grupo o ACL mínima según cada lector,
sin hacer los secretos world-readable. La prueba Windows no acredita esta
configuración POSIX. Mantener directorios privados y claves TLS fuera del árbol.

Validación futura de configuración, sin imprimir el YAML interpolado:

```text
docker compose --project-name PROYECTO_AZURE_NUEVO --env-file RUTAS_EXTERNAS -f deploy/azure/compose.azure.yaml --profile approved-azure-runtime config --quiet
```

No se incluyen órdenes `up`, migración, bootstrap, NSG o SSH como pasos
autorizados por esta guía. El despliegue deberá verificar primero todas las
puertas y obtener permiso propio. Detener solo el proyecto autorizado sin-v;
no usar prune ni restaurar un volumen sobre otro destino. Para una actualización
con datos: respaldo privado y recuperación verificada antes de cambiar imagen.

## Evidencia estática y límites

Macro E ejecutó cuatro pruebas offline del renderizador, Compose config con
fixtures y `nginx -t` en contenedor sin red. Usó el FQDN sintético
`recon-static.example.test` y TLS de laboratorio, **no certificado público**.
No se ejecutaron SSH, DNS cloud, NSG, creación de recursos o despliegue Azure.
La versión se identifica por el SHA de la publicación verificada en el acta externa Macro F. No se presume desplegada. Incremento0010 ABIERTO.

La edición humana posterior Bienvenido debe llegar al build desde ese SHA; no se encuentra en la imagen frontend del ensayo E. Macro F verificó el texto en fuente, compilación y navegador con API ficticia, sin cambiar esta configuración ni desplegar.
