# Pruebas y límites del Macro B

- E0 integral PASS, sin secretos/servicios/DB; delta PASS de auxiliares afectados.
- Tres casos ficticios del parser privado PASS; ninguna clave real generada.
- C0: un intento de conexión, error MySQL 1045 antes de SELECT; FAIL/STOP.
- G6 real, roles, HTTP, zoom/Narrador: NO EJECUTADOS.
- 17/17 pruebas nuevas de proxy/secretos/configuración de contenedor PASS.
- Diez verificaciones estructurales Docker/Nginx/contextos PASS.
- Docker Compose config --quiet PASS, fixtures externas inertes sin secretos.
- Ruff PASS sobre src/tests/scripts/deploy y verificador raíz.
- 189 pruebas frontend A y suites backend previas: REUTILIZADAS, no repetidas.
- Hadolint, nginx -t, build/up, TLS, migraciones y E2E Docker: NO EJECUTADOS.

Las pruebas nuevas viven en
[test_deploy_wsgi.py](../../backend/tests/unit/test_deploy_wsgi.py).
Se ejecutaron solo esas pruebas, con plugins externos desactivados, veto de
sockets/subprocesos, tmp externo, sin pycache ni pytest cache. No se conectó
SQL ni se leyó un secreto real dentro de ellas.

Desde raíz, para la validación estática autorizada:

```powershell
python -B scripts/validar_docker_estatico.py
```

Para los nuevos tests, con el entorno ya instalado, desde backend:

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_deploy_wsgi.py -q -p no:cacheprovider
```

El runner exacto usado añade auditoría de red/procesos, entorno limpio y
basetemp/JUnit externos; está en las evidencias ZIP. Los comandos no conceden
autorización de servicios, contenedores, migraciones o datos.

La factory inerte E0 y el proxy con DNS simulado no certifican MySQL, resolución
Docker real, cookies en navegador, TLS ni despliegue. C15/D08/D09/D13 y D12
humano se conservan. No se presenta una configuración válida como build PASS.
