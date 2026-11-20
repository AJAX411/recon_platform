"""Validación sin daemon/build/up ni secretos; Compose usa fixtures externas inertes."""

import ast
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    checks = []

    def check(name, condition):
        if not condition:
            raise ValueError("Comprobación estática fallida: " + name)
        checks.append({"id": name, "result": "PASS_ESTRUCTURAL"})

    backend = (ROOT / "backend/Dockerfile").read_text(encoding="utf-8")
    frontend = (ROOT / "frontend/Dockerfile").read_text(encoding="utf-8")
    nginx = (ROOT / "frontend/nginx.conf").read_text(encoding="utf-8")
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    check("backend_python_314_usuario_wsgi_sin_migracion", all(s in backend for s in (
        "python:3.14.10-slim-bookworm@sha256:", "USER 10001:10001", '"gunicorn"', "--only-binary=:all:"))
        and not any(s in backend for s in ("flask run", "db upgrade", "db migrate")))
    check("frontend_multietapa_lock_sin_legacy", "AS build" in frontend and "AS runtime" in frontend
          and "npm ci --ignore-scripts" in frontend and "package-lock.json" in frontend
          and "COPY frontend/ ." not in frontend and "USER nginx" in frontend)
    check("nginx_spa_api_https_sin_forwarded_usuario", all(s in nginx for s in (
        "try_files $uri $uri/ /index.html", "proxy_pass http://backend:8000;",
        "listen 8443 ssl", "proxy_set_header X-Forwarded-Proto $scheme;",
        'proxy_set_header X-Forwarded-For "";', "access_log off;")))
    check("nginx_equilibrio_llaves_basico", nginx.count("{") == nginx.count("}"))
    check("compose_publica_solo_frontend_loopback", compose.count("ports:") == 1
          and '127.0.0.1:${RECON_HTTPS_PORT:-8443}:8443' in compose
          and "recon_dev" not in compose and "recon_tests" not in compose)
    check("compose_privado_perfiles_y_secretos_file", compose.count("internal: true") == 2
          and compose.count("profiles: [approved-runtime]") == 3
          and "MYSQL_PASSWORD_FILE" in compose and "SECRET_KEY_FILE" in compose)
    check("entrada_local_solo_frontend_sin_snat", "networks: [web, entrada_local]" in compose
          and 'com.docker.network.bridge.host_binding_ipv4: "127.0.0.1"' in compose
          and 'com.docker.network.bridge.enable_ip_masquerade: "false"' in compose)
    check("sin_secretos_baked", not re.search(r"(?im)^\s*(?:ARG|ENV)\s+\w*(?:PASSWORD|SECRET_KEY)\s*=", backend + frontend))
    for name in ("backend", "frontend"):
        ignore = (ROOT / name / "Dockerfile.dockerignore").read_text(encoding="utf-8")
        check(name + "_contexto_raiz_whitelist", ignore.splitlines()[1] == "**"
              and "**/.env" in ignore and "**/node_modules" in ignore)
    ast.parse((ROOT / "backend/deploy/app_wsgi.py").read_text(encoding="utf-8"))
    check("adaptador_wsgi_ast", True)

    docker = shutil.which("docker")
    result = {"structural_checks": checks, "Dockerfiles_real_lint": "NO EJECUTADO por este verificador: sin hadolint",
              "nginx_t": "FUERA DEL VERIFICADOR ESTÁTICO: consultar evidencia de ejecución Docker",
              "build_up_migrations": "FUERA DEL VERIFICADOR ESTÁTICO; no ejecuta esas operaciones",
              "image_digests_and_tag_availability": "FUERA DEL VERIFICADOR ESTÁTICO: consultar registro y evidencia separados"}
    if docker:
        # Solo modelo de configuración; no requiere motor y no crea recursos.
        parent = Path(tempfile.gettempdir()).resolve()
        with tempfile.TemporaryDirectory(prefix="recon_compose_static_", dir=parent) as folder:
            target = Path(folder).resolve()
            if target.parent != parent or not target.name.startswith("recon_compose_static_"):
                raise ValueError("El directorio temporal no coincide con el destino previsto.")
            sample = target / "fixture_static"
            sample.write_text("STATIC_PLACEHOLDER_NOT_A_SECRET", encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k.upper() in {
                "SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "COMSPEC", "PROGRAMFILES", "PROGRAMFILES(X86)"}}
            for name in ("RECON_DB_ROOT_PASSWORD_FILE", "RECON_DB_APP_PASSWORD_FILE",
                         "RECON_SESSION_KEY_FILE", "RECON_TLS_CERT_FILE", "RECON_TLS_KEY_FILE"):
                env[name] = sample.as_posix()
            env["COMPOSE_DISABLE_ENV_FILE"] = "1"
            out = subprocess.run([docker, "compose", "--env-file", str(ROOT / "deploy/container.env.example"),
                                  "-f", str(ROOT / "compose.yaml"), "config", "--quiet"],
                                 cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            result["compose_config_quiet"] = {"exitCode": out.returncode,
                                              "result": "PASS_SINTAXIS" if out.returncode == 0 else "FAIL",
                                              "secret_source": "fixture externa inerte, no valores reales"}
            if out.returncode:
                raise ValueError("Compose config --quiet no satisfactorio; revisar modelo sin mostrar variables.")
    else:
        result["compose_config_quiet"] = {"result": "NO EJECUTADO: CLI ausente"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
