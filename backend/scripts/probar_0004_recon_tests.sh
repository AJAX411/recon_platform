#!/usr/bin/env bash
# Procedimiento manual posterior a 0004: integración real, solo con autorización.
set -Eeuo pipefail
if (( $# != 0 )) || [[ "${RECON_AUTORIZAR_PRUEBAS_MYSQL_0004:-}" != 1 ]]; then
    printf 'Se exige autorización posterior explícita: RECON_AUTORIZAR_PRUEBAS_MYSQL_0004=1.\n' >&2
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
    unset RECON_AUTORIZAR_PRUEBAS_MYSQL_0004
    if (( resultado != 0 )); then
        printf 'DETENIDO. Revisar la base de pruebas; no reintentar automáticamente.\n' >&2
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
"$python_bin" -B scripts/verificar_recon_tests_0004.py --despues
export RECON_RUN_MYSQL_INTEGRATION=1
set +e
"$python_bin" -B -m pytest -p no:cacheprovider tests/integration
resultado_pruebas=$?
set -e
unset RECON_RUN_MYSQL_INTEGRATION
"$python_bin" -B scripts/verificar_recon_tests_0004.py --despues
if (( resultado_pruebas != 0 )); then
    printf 'Las pruebas fallaron; la verificación posterior sí se completó.\n' >&2
    exit "$resultado_pruebas"
fi
printf 'Integración terminada; no quedaron residuos de pruebas.\n'
