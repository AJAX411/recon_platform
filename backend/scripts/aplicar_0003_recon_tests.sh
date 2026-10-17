#!/usr/bin/env bash
# Procedimiento manual: respaldo y migración dirigida, solo tras aprobación.
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
    printf 'No se encontró el entorno virtual del backend.\n' >&2
    exit 1
fi
if [[ -f '/c/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump.exe' ]]; then
    mysqldump_bin='/c/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump.exe'
elif command -v mysqldump.exe >/dev/null 2>&1; then
    mysqldump_bin="$(command -v mysqldump.exe)"
else
    printf 'Se requiere mysqldump.exe de MySQL 8.0.\n' >&2
    exit 1
fi

limpiar() {
    resultado=$?
    unset DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD DB_TEST_NAME DB_TEST_USER DB_TEST_PASSWORD
    unset SECRET_KEY MYSQL_PWD FLASK_SKIP_DOTENV RECON_RUN_MYSQL_INTEGRATION
    if (( resultado != 0 )); then
        printf 'DETENIDO. Revisar el estado; no reintentar ni borrar tablas automáticamente.\n' >&2
    fi
}
trap limpiar EXIT

unset DB_USER DB_PASSWORD MYSQL_PWD RECON_RUN_MYSQL_INTEGRATION
export DB_HOST=127.0.0.1 DB_PORT=3306 DB_NAME=recon_dev
export DB_TEST_NAME=recon_tests DB_TEST_USER=recon_test_app FLASK_SKIP_DOTENV=1
read -r -s -p 'Contraseña de recon_test_app para la aplicación: ' DB_TEST_PASSWORD
printf '\n'
if [[ -z "$DB_TEST_PASSWORD" ]]; then
    printf 'La contraseña no puede estar vacía.\n' >&2
    exit 1
fi
export DB_TEST_PASSWORD

printf 'Comprobación previa de lectura...\n'
"$python_bin" -B scripts/verificar_recon_tests_0003.py --antes

home_dir="$(cd -- "${HOME:?}" && pwd -P)"
backup_root="$home_dir/ReconFacialBackups"
mkdir -p -- "$backup_root"
backup_root="$(cd -- "$backup_root" && pwd -P)"
case "$backup_root/" in
    "$repo_dir/"*)
        printf 'El respaldo debe quedar fuera del repositorio.\n' >&2
        exit 1
        ;;
esac
chmod 700 -- "$backup_root"
backup_dir="$(mktemp -d "$backup_root/recon_tests_pre_0003_XXXXXXXX")"
backup_partial="$backup_dir/recon_tests_0002.partial.sql"
backup_file="$backup_dir/recon_tests_0002.sql"
printf 'Generando respaldo privado fuera del repositorio: %s\n' "$backup_dir"
printf 'mysqldump solicitará de nuevo la contraseña, sin mostrarla.\n'
(
    unset DB_TEST_PASSWORD MYSQL_PWD
    "$mysqldump_bin" --no-defaults \
        --protocol=TCP --host=127.0.0.1 --port=3306 \
        --user=recon_test_app --password \
        --single-transaction --quick --no-tablespaces \
        --column-statistics=0 --set-gtid-purged=OFF \
        --default-character-set=utf8mb4 \
        --result-file="$backup_partial" recon_tests
)
if [[ ! -s "$backup_partial" ]]; then
    printf 'Respaldo vacío.\n' >&2
    exit 1
fi
for tabla in alembic_version tipo_persona persona rol usuario_plataforma auditoria_iam; do
    if ! grep -Fq "CREATE TABLE \`$tabla\`" "$backup_partial"; then
        printf 'Falta una tabla requerida en el respaldo.\n' >&2
        exit 1
    fi
done
if ! grep -Fq '0002_identity_iam' "$backup_partial"; then
    printf 'El respaldo no contiene la revisión Alembic previa.\n' >&2
    exit 1
fi
if ! grep -Fq 'Dump completed on' "$backup_partial"; then
    printf 'El respaldo no contiene la marca de finalización.\n' >&2
    exit 1
fi
mv -- "$backup_partial" "$backup_file"
printf 'Respaldo completo; comprobación previa inmediata...\n'
"$python_bin" -B scripts/verificar_recon_tests_0003.py --antes

printf 'Aplicando exclusivamente 0003_sesiones_iam en recon_tests...\n'
"$python_bin" -B -m flask \
    --app 'recon_platform:create_app(pruebas=True)' \
    db upgrade 0003_sesiones_iam

printf 'Comprobación posterior de solo lectura...\n'
"$python_bin" -B scripts/verificar_recon_tests_0003.py --despues
printf 'Procedimiento terminado. Conservar el respaldo fuera del repositorio: %s\n' "$backup_file"
