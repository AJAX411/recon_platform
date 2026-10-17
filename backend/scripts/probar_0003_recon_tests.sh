#!/usr/bin/env bash
# Pruebas reales de integración: ejecutar solo tras autorización y migración 0003.
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
limpiar() {
    resultado=$?
    unset DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD DB_TEST_NAME DB_TEST_USER DB_TEST_PASSWORD
    unset SECRET_KEY MYSQL_PWD FLASK_SKIP_DOTENV RECON_RUN_MYSQL_INTEGRATION
    if (( resultado != 0 )); then
        printf 'DETENIDO. Revisar el estado de pruebas; no reintentar automáticamente.\n' >&2
    fi
}
trap limpiar EXIT
unset DB_USER DB_PASSWORD MYSQL_PWD
export DB_HOST=127.0.0.1 DB_PORT=3306 DB_NAME=recon_dev
export DB_TEST_NAME=recon_tests DB_TEST_USER=recon_test_app FLASK_SKIP_DOTENV=1
read -r -s -p 'Contraseña de recon_test_app para integración: ' DB_TEST_PASSWORD
printf '\n'
if [[ -z "$DB_TEST_PASSWORD" ]]; then
    printf 'La contraseña no puede estar vacía.\n' >&2
    exit 1
fi
export DB_TEST_PASSWORD
"$python_bin" -B scripts/verificar_recon_tests_0003.py --despues
export RECON_RUN_MYSQL_INTEGRATION=1
"$python_bin" -B -m pytest -p no:cacheprovider tests/integration
unset RECON_RUN_MYSQL_INTEGRATION
"$python_bin" -B scripts/verificar_recon_tests_0003.py --despues
printf 'Integración terminada; no quedaron datos temporales IAM.\n'
