#!/usr/bin/env bash
# Prueba manual HTTP local del SUPERADMIN; ejecutar solo tras autorización.
set -Eeuo pipefail

if (( $# != 0 )); then
    printf 'Este procedimiento no acepta argumentos.\n' >&2
    exit 1
fi
scripts_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
backend_dir="$(cd -- "$scripts_dir/.." && pwd -P)"
cd -- "$backend_dir"
python_bin="$backend_dir/.venv/Scripts/python.exe"
if [[ ! -f "$python_bin" ]]; then
    printf 'No se encontró el entorno virtual del backend.\n' >&2
    exit 1
fi
if [[ ! -t 0 ]]; then
    printf 'Se requiere una terminal interactiva para la entrada oculta.\n' >&2
    exit 1
fi

limpiar() {
    resultado=$?
    unset DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD DB_TEST_NAME DB_TEST_USER DB_TEST_PASSWORD
    unset MYSQL_PWD SECRET_KEY FLASK_SKIP_DOTENV RECON_LOCAL_HTTP
    unset RECON_SESSION_COOKIE_SECURE RECON_RUN_MYSQL_INTEGRATION
    if (( resultado != 0 )); then
        printf 'DETENIDO. Revisar la salida; no repetir el login automáticamente.\n' >&2
    fi
}
trap limpiar EXIT

unset DB_TEST_NAME DB_TEST_USER DB_TEST_PASSWORD MYSQL_PWD SECRET_KEY
unset RECON_RUN_MYSQL_INTEGRATION
export DB_HOST=127.0.0.1 DB_PORT=3306 DB_NAME=recon_dev DB_USER=recon_dev_app
export FLASK_SKIP_DOTENV=1 RECON_LOCAL_HTTP=1 RECON_SESSION_COOKIE_SECURE=0
read -r -s -p 'Contraseña de recon_dev_app (oculta): ' DB_PASSWORD
printf '\n'
if [[ -z "$DB_PASSWORD" ]]; then
    printf 'La contraseña MySQL no puede estar vacía.\n' >&2
    exit 1
fi
export DB_PASSWORD

"$python_bin" -B scripts/probar_http_superadmin_recon_dev.py
