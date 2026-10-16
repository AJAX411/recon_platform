#!/usr/bin/env bash
# Ejecución manual y dirigida de 0002_identity_iam en recon_dev.
set -Eeuo pipefail
umask 077

if (( $# != 0 )); then
    printf 'Este procedimiento no acepta argumentos.\n' >&2
    exit 1
fi

scripts_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
backend_dir="$(cd -- "$scripts_dir/.." && pwd -P)"
repo_dir="$(cd -- "$backend_dir/.." && pwd -P)"
cd -- "$backend_dir"

python_bin="$backend_dir/.venv/Scripts/python.exe"
if [[ ! -f "$python_bin" ]]; then
    printf 'No se encontró el Python del entorno virtual del backend.\n' >&2
    exit 1
fi

if [[ -f '/c/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump.exe' ]]; then
    mysqldump_bin='/c/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump.exe'
elif command -v mysqldump.exe >/dev/null 2>&1; then
    mysqldump_bin="$(command -v mysqldump.exe)"
elif command -v mysqldump >/dev/null 2>&1; then
    mysqldump_bin="$(command -v mysqldump)"
else
    printf 'No se encontró mysqldump de MySQL 8.0. Detenido.\n' >&2
    exit 1
fi

limpiar() {
    resultado=$?
    unset DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD FLASK_SKIP_DOTENV
    if (( resultado != 0 )); then
        printf 'DETENIDO. No reintentar ni borrar tablas; revisar el estado antes de actuar.\n' >&2
    fi
}
trap limpiar EXIT

# Estas variables solo viven en este proceso Bash y sus hijos.
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_NAME=recon_dev
export DB_USER=recon_dev_app
export FLASK_SKIP_DOTENV=1
read -r -s -p 'Contraseña de recon_dev_app para la aplicación: ' DB_PASSWORD
printf '\n'
if [[ -z "$DB_PASSWORD" ]]; then
    printf 'La contraseña no puede estar vacía.\n' >&2
    exit 1
fi
export DB_PASSWORD

printf 'Comprobación previa de destino, revisión y Persona...\n'
"$python_bin" -B scripts/verificar_recon_dev.py

home_dir="$(cd -- "${HOME:?}" && pwd -P)"
backup_root="$home_dir/ReconFacialBackups"
mkdir -p -- "$backup_root"
backup_root="$(cd -- "$backup_root" && pwd -P)"
case "$backup_root/" in
    "$repo_dir/"*)
        printf 'El respaldo debe quedar fuera del repositorio. Detenido.\n' >&2
        exit 1
        ;;
esac
chmod 700 -- "$backup_root"
backup_dir="$(mktemp -d "$backup_root/recon_dev_pre_0002_XXXXXXXX")"
backup_partial="$backup_dir/recon_dev_0001.partial.sql"
backup_file="$backup_dir/recon_dev_0001.sql"

printf 'Creando respaldo privado en %s\n' "$backup_dir"
printf 'mysqldump solicitará de nuevo la contraseña de recon_dev_app de forma oculta.\n'
(
    unset DB_PASSWORD MYSQL_PWD
    "$mysqldump_bin" --no-defaults \
        --protocol=TCP --host=127.0.0.1 --port=3306 \
        --user=recon_dev_app --password \
        --single-transaction --quick --no-tablespaces \
        --column-statistics=0 --set-gtid-purged=OFF \
        --default-character-set=utf8mb4 \
        --result-file="$backup_partial" recon_dev
)
if [[ ! -s "$backup_partial" ]]; then
    printf 'El archivo de respaldo está vacío. Detenido.\n' >&2
    exit 1
fi
for tabla in alembic_version tipo_persona persona; do
    if ! grep -Fq "CREATE TABLE \`$tabla\`" "$backup_partial"; then
        printf 'Falta una tabla requerida en el respaldo. Detenido.\n' >&2
        exit 1
    fi
done
if ! grep -Fq 'INSERT INTO `persona`' "$backup_partial"; then
    printf 'El respaldo no contiene filas de Persona. Detenido.\n' >&2
    exit 1
fi
mv -- "$backup_partial" "$backup_file"
printf 'Respaldo generado y comprobado de forma básica.\n'

# Repetir inmediatamente antes de la única operación que cambia MySQL.
"$python_bin" -B scripts/verificar_recon_dev.py
printf 'Aplicando únicamente la revisión 0002_identity_iam en recon_dev...\n'
"$python_bin" -B -m flask \
    --app 'recon_platform:create_app(pruebas=False)' \
    db upgrade 0002_identity_iam

printf 'Verificación posterior de solo lectura...\n'
"$python_bin" -B scripts/verificar_recon_dev_0002.py
printf 'Procedimiento terminado. Conservar el respaldo fuera del repositorio: %s\n' "$backup_file"
