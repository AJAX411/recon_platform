#!/usr/bin/env bash
# Procedimiento manual para crear el primer SUPERADMIN solo en recon_dev.
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
    printf 'No se encontró el Python del entorno virtual del backend.\n' >&2
    exit 1
fi

limpiar() {
    resultado=$?
    unset DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD FLASK_SKIP_DOTENV
    if (( resultado != 0 )); then
        printf 'DETENIDO. No repetir el bootstrap sin revisar el estado de recon_dev.\n' >&2
    fi
}
trap limpiar EXIT

# El proceso hijo nunca recibe credenciales de pruebas ni carga archivos .env.
unset DB_TEST_NAME DB_TEST_USER DB_TEST_PASSWORD
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_NAME=recon_dev
export DB_USER=recon_dev_app
export FLASK_SKIP_DOTENV=1
read -r -s -p 'Contraseña de recon_dev_app: ' DB_PASSWORD
printf '\n'
if [[ -z "$DB_PASSWORD" ]]; then
    printf 'La contraseña de MySQL no puede estar vacía.\n' >&2
    exit 1
fi
export DB_PASSWORD

# Requiere revisión 0002, esquema intacto y cero cuentas/auditorías.
"$python_bin" -B scripts/verificar_recon_dev_0002.py

printf 'Inicialización explícita del primer SUPERADMIN en recon_dev.\n'
"$python_bin" -B -m flask \
    --app 'recon_platform:create_app(pruebas=False)' \
    bootstrap-superadmin

# Consultas SELECT; no muestra login, contraseña ni hash.
"$python_bin" -B scripts/verificar_superadmin_recon_dev.py
printf 'Bootstrap y verificación posterior completados.\n'
