#!/usr/bin/env bash
# Procedimiento preparado; ejecutarlo solo tras revisión y autorización expresa.
set -Eeuo pipefail
umask 077

if (( $# != 0 )) || [[ "${RECON_AUTORIZAR_MIGRACION_0005_RECON_TESTS:-}" != 1 ]]; then
    printf 'Se exige RECON_AUTORIZAR_MIGRACION_0005_RECON_TESTS=1.\n' >&2
    exit 1
fi
scripts_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
backend_dir="$(cd -- "$scripts_dir/.." && pwd -P)"
repo_dir="$(cd -- "$backend_dir/.." && pwd -P)"
cd -- "$backend_dir"
python_bin="$backend_dir/.venv/Scripts/python.exe"
if [[ ! -f "$python_bin" ]]; then
    printf 'No se encontró el Python del backend.\n' >&2
    exit 1
fi
if [[ -f '/c/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump.exe' ]]; then
    mysqldump_bin='/c/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump.exe'
elif command -v mysqldump.exe >/dev/null 2>&1; then
    mysqldump_bin="$(command -v mysqldump.exe)"
else
    printf 'Se requiere mysqldump.exe.\n' >&2
    exit 1
fi
if ! command -v icacls.exe >/dev/null 2>&1 ||
   ! command -v cygpath >/dev/null 2>&1 ||
   ! command -v powershell.exe >/dev/null 2>&1; then
    printf 'Se requieren icacls.exe, cygpath y PowerShell para proteger el respaldo.\n' >&2
    exit 1
fi
limpiar() {
    resultado=$?
    unset admin_user admin_password RECON_BACKUP_ADMIN_USER RECON_BACKUP_ADMIN_PASSWORD
    unset DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD DB_TEST_NAME DB_TEST_USER DB_TEST_PASSWORD
    unset SECRET_KEY MYSQL_PWD FLASK_SKIP_DOTENV RECON_RUN_MYSQL_INTEGRATION
    unset RECON_AUTORIZAR_MIGRACION_0005_RECON_TESTS
    if (( resultado != 0 )); then
        printf 'DETENIDO. Conservar respaldo y revisar estado; no restaurar ni reintentar automáticamente.\n' >&2
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
"$python_bin" -B scripts/verificar_recon_tests_0005.py --antes
read -r -p 'Cuenta administrativa para verificar objetos almacenados: ' admin_user
read -r -s -p 'Contraseña de la cuenta administrativa: ' admin_password
printf '\n'
if [[ -z "$admin_user" || -z "$admin_password" ]]; then
    printf 'Se exige cuenta administrativa independiente.\n' >&2
    exit 1
fi
RECON_BACKUP_ADMIN_USER="$admin_user" RECON_BACKUP_ADMIN_PASSWORD="$admin_password" \
    "$python_bin" -B scripts/verificar_objetos_recon_tests_0005.py

backup_root="$(cd -- "${HOME:?}" && pwd -P)/ReconFacialBackups"
mkdir -p -- "$backup_root"
backup_root="$(cd -- "$backup_root" && pwd -P)"
case "$backup_root/" in
    "$repo_dir/"*) printf 'El respaldo debe quedar fuera del repositorio.\n' >&2; exit 1 ;;
esac
backup_dir="$(mktemp -d "$backup_root/recon_tests_pre_0005_XXXXXXXX")"
sid="$(powershell.exe -NoProfile -NonInteractive -Command \
    '[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value' | tr -d '\r\n')"
if [[ ! "$sid" =~ ^S-[0-9]+(-[0-9]+)+$ ]]; then
    printf 'No se pudo identificar la cuenta Windows.\n' >&2
    exit 1
fi
if ! MSYS_NO_PATHCONV=1 icacls.exe "$(cygpath -w "$backup_dir")" \
    /inheritance:r /grant:r "*${sid}:(OI)(CI)F" >/dev/null; then
    printf 'No se pudieron proteger los archivos de respaldo.\n' >&2
    exit 1
fi
backup_partial="$backup_dir/recon_tests_0004.partial.sql"
backup_file="$backup_dir/recon_tests_0004.sql"
printf 'Respaldo privado completo fuera del repositorio. mysqldump solicitará la contraseña otra vez.\n'
(
    unset DB_TEST_PASSWORD MYSQL_PWD
    "$mysqldump_bin" --no-defaults --protocol=TCP --host=127.0.0.1 --port=3306 \
        --user=recon_test_app --password --single-transaction --quick --no-tablespaces \
        --column-statistics=0 --set-gtid-purged=OFF --default-character-set=utf8mb4 \
        --skip-routines --skip-events --skip-triggers \
        --result-file="$backup_partial" recon_tests
)
if [[ ! -s "$backup_partial" ]]; then
    printf 'Respaldo vacío.\n' >&2
    exit 1
fi
for tabla in alembic_version tipo_persona persona rol usuario_plataforma auditoria_iam sesion_usuario auditoria_personas; do
    if ! grep -Fq "CREATE TABLE \`$tabla\`" "$backup_partial"; then
        printf 'Falta una tabla requerida en el respaldo.\n' >&2
        exit 1
    fi
done
if ! grep -Fq 'INSERT INTO `rol`' "$backup_partial" ||
   ! grep -Fq '0004_auditoria_personas' "$backup_partial" ||
   ! grep -Fq 'Dump completed on' "$backup_partial"; then
    printf 'No se acredita revisión previa o fin del respaldo.\n' >&2
    exit 1
fi
mv -- "$backup_partial" "$backup_file"
"$python_bin" -B scripts/verificar_recon_tests_0005.py --antes
RECON_BACKUP_ADMIN_USER="$admin_user" RECON_BACKUP_ADMIN_PASSWORD="$admin_password" \
    "$python_bin" -B scripts/verificar_objetos_recon_tests_0005.py
read -r -p 'Para aplicar 0005 solo en recon_tests, escriba APLICAR_0005_RECON_TESTS: ' confirmacion
if [[ "$confirmacion" != APLICAR_0005_RECON_TESTS ]]; then
    printf 'Confirmación incorrecta; no se aplicó la migración.\n' >&2
    exit 1
fi
"$python_bin" -B -m flask --app 'recon_platform:create_app(pruebas=True)' \
    db upgrade 0005_puntos_edge_auditoria
"$python_bin" -B scripts/verificar_recon_tests_0005.py --despues
printf '0005 verificada en recon_tests. Conservar respaldo privado: %s\n' "$backup_file"
