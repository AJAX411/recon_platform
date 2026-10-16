"""Comprobación manual de solo lectura tras 0002_identity_iam en recon_dev."""

import os
import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.pool import NullPool

from recon_platform.config import obtener_uri_mysql

DESTINO = ("127.0.0.1", 3306, "recon_dev", "recon_dev_app")
VARIABLES = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
TABLAS = {
    "alembic_version", "tipo_persona", "persona",
    "rol", "usuario_plataforma", "auditoria_iam",
}
ROLES = {"SUPERADMIN", "ADMINISTRADOR", "OPERADOR"}


class VerificacionFallida(Exception):
    """Discrepancia que exige detener el procedimiento."""


def verificar_esquema(conexion: Connection) -> None:
    inspector = inspect(conexion)
    columnas_esperadas = {
        "rol": {"id_rol", "nombre"},
        "usuario_plataforma": {
            "id_usuario", "login", "hash_contrasena", "id_rol", "estado",
            "fecha_creacion", "fecha_actualizacion",
        },
        "auditoria_iam": {
            "id_auditoria", "actor_id", "usuario_id", "accion", "resultado",
            "anterior", "nuevo", "fecha",
        },
    }
    anulables_esperadas = {
        "rol": set(),
        "usuario_plataforma": set(),
        "auditoria_iam": {"actor_id", "anterior", "nuevo"},
    }
    claves_primarias = {
        "rol": ["id_rol"],
        "usuario_plataforma": ["id_usuario"],
        "auditoria_iam": ["id_auditoria"],
    }
    for tabla, nombres in columnas_esperadas.items():
        columnas = {columna["name"]: columna for columna in inspector.get_columns(tabla)}
        if set(columnas) != nombres:
            raise VerificacionFallida(f"Columnas inesperadas en {tabla}.")
        if {
            nombre for nombre, columna in columnas.items() if columna["nullable"]
        } != anulables_esperadas[tabla]:
            raise VerificacionFallida(f"Nulabilidad inesperada en {tabla}.")
        if inspector.get_pk_constraint(tabla)["constrained_columns"] != claves_primarias[tabla]:
            raise VerificacionFallida(f"Clave primaria inesperada en {tabla}.")

    unicidades = {
        tabla: {
            unica["name"]: unica["column_names"]
            for unica in inspector.get_unique_constraints(tabla)
        }
        for tabla in ("rol", "usuario_plataforma")
    }
    if unicidades != {
        "rol": {"uq_rol_nombre": ["nombre"]},
        "usuario_plataforma": {"uq_usuario_plataforma_login": ["login"]},
    }:
        raise VerificacionFallida("Restricciones UNIQUE de IAM inesperadas.")

    for tabla, nombre_esperado in (
        ("rol", "ck_rol_nombre_aprobado"),
        ("usuario_plataforma", "ck_usuario_plataforma_estado"),
    ):
        resultado_checks = conexion.execute(text(
            "SELECT CONSTRAINT_NAME, ENFORCED "
            "FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :tabla "
            "AND CONSTRAINT_TYPE = 'CHECK'"
        ), {"tabla": tabla})
        checks: dict[str, str] = {}
        for fila in resultado_checks.mappings():
            nombre = fila["CONSTRAINT_NAME"]
            aplicado = fila["ENFORCED"]
            if not isinstance(nombre, str) or not isinstance(aplicado, str):
                raise VerificacionFallida(f"Restricciones CHECK de {tabla} ilegibles.")
            checks[nombre] = aplicado
        if checks != {nombre_esperado: "YES"}:
            raise VerificacionFallida(f"Restricciones CHECK de {tabla} inesperadas.")

    relaciones = {
        tabla: {
            fk["name"]: (
                fk["constrained_columns"], fk["referred_table"],
                fk["referred_columns"],
            )
            for fk in inspector.get_foreign_keys(tabla)
        }
        for tabla in ("rol", "usuario_plataforma", "auditoria_iam")
    }
    if relaciones != {
        "rol": {},
        "usuario_plataforma": {
            "fk_usuario_plataforma_rol": (["id_rol"], "rol", ["id_rol"]),
        },
        "auditoria_iam": {
            "fk_auditoria_iam_actor": (
                ["actor_id"], "usuario_plataforma", ["id_usuario"]
            ),
            "fk_auditoria_iam_usuario": (
                ["usuario_id"], "usuario_plataforma", ["id_usuario"]
            ),
        },
    }:
        raise VerificacionFallida("Claves foráneas de IAM inesperadas.")

    resultado_fk = conexion.execute(text(
        "SELECT CONSTRAINT_NAME, DELETE_RULE "
        "FROM information_schema.REFERENTIAL_CONSTRAINTS "
        "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME IN "
        "('usuario_plataforma', 'auditoria_iam')"
    ))
    reglas_fk: dict[str, str] = {}
    for fila in resultado_fk.mappings():
        nombre = fila["CONSTRAINT_NAME"]
        regla = fila["DELETE_RULE"]
        if not isinstance(nombre, str) or not isinstance(regla, str):
            raise VerificacionFallida("Reglas de eliminación de IAM ilegibles.")
        reglas_fk[nombre] = regla
    if reglas_fk != {
        "fk_usuario_plataforma_rol": "RESTRICT",
        "fk_auditoria_iam_actor": "RESTRICT",
        "fk_auditoria_iam_usuario": "RESTRICT",
    }:
        raise VerificacionFallida("Reglas de eliminación de IAM inesperadas.")


def verificar() -> None:
    ausentes = [nombre for nombre in VARIABLES if not os.getenv(nombre)]
    if ausentes:
        raise VerificacionFallida(
            "Faltan variables de entorno: " + ", ".join(ausentes) + "."
        )

    uri = obtener_uri_mysql(pruebas=False)
    if uri is None:
        raise VerificacionFallida("La configuración MySQL de desarrollo está incompleta.")
    url = make_url(uri)
    if (
        url.drivername != "mysql+pymysql"
        or (url.host, url.port, url.database, url.username) != DESTINO
    ):
        raise VerificacionFallida(
            "Destino configurado no autorizado: se exige "
            "127.0.0.1:3306/recon_dev con recon_dev_app."
        )

    motor = create_engine(url, poolclass=NullPool)
    try:
        with motor.connect() as conexion:
            base, cuenta, usuario, puerto = conexion.execute(
                text("SELECT DATABASE(), CURRENT_USER(), USER(), @@port")
            ).one()
            if (
                base != "recon_dev"
                or cuenta.partition("@")[0] != "recon_dev_app"
                or usuario.partition("@")[0] != "recon_dev_app"
                or puerto != 3306
            ):
                raise VerificacionFallida(
                    "La identidad real de la conexión no corresponde a recon_dev."
                )

            resultado_tablas = conexion.execute(text(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN "
                "('alembic_version', 'tipo_persona', 'persona', "
                "'rol', 'usuario_plataforma', 'auditoria_iam')"
            ))
            tablas: dict[str, str] = {}
            for fila in resultado_tablas.mappings():
                nombre = fila["TABLE_NAME"]
                motor_tabla = fila["ENGINE"]
                if not isinstance(nombre, str) or not isinstance(motor_tabla, str):
                    raise VerificacionFallida("No se pudo validar el esquema MySQL.")
                tablas[nombre] = motor_tabla
            if not TABLAS.issubset(tablas):
                raise VerificacionFallida("Faltan tablas de Personas o Identity/IAM.")
            if any(tablas[nombre] != "InnoDB" for nombre in TABLAS):
                raise VerificacionFallida("Alguna tabla requerida no utiliza InnoDB.")

            revisiones = conexion.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalars().all()
            if revisiones != ["0002_identity_iam"]:
                raise VerificacionFallida(
                    "La revisión Alembic actual no es exactamente 0002_identity_iam."
                )

            verificar_esquema(conexion)
            roles = conexion.execute(text("SELECT nombre FROM rol")).scalars().all()
            if len(roles) != 3 or set(roles) != ROLES:
                raise VerificacionFallida("El catálogo inicial de roles es inesperado.")
            for consulta in (
                "SELECT COUNT(*) FROM usuario_plataforma",
                "SELECT COUNT(*) FROM auditoria_iam",
            ):
                cantidad = conexion.execute(text(consulta)).scalar_one()
                if cantidad != 0:
                    raise VerificacionFallida(
                        "Se encontraron cuentas o auditorías IAM inesperadas."
                    )
            persona_presente = conexion.execute(text(
                "SELECT 1 FROM persona WHERE id_persona = 1 LIMIT 1"
            )).scalar_one_or_none()
            if persona_presente != 1:
                raise VerificacionFallida(
                    "No se encontró la Persona de desarrollo con id_persona=1."
                )
    finally:
        motor.dispose()


def main() -> int:
    if len(sys.argv) != 1:
        print("NO APTO: este verificador no acepta argumentos.", file=sys.stderr)
        return 1
    try:
        verificar()
    except VerificacionFallida as error:
        print(f"NO APTO: {error}", file=sys.stderr)
        return 1
    except Exception:
        # No mostrar excepciones del controlador: pueden incluir la URL o credenciales.
        print(
            "NO APTO: no se pudo completar la comprobación autenticada de MySQL.",
            file=sys.stderr,
        )
        return 1

    print("APTO: destino y cuenta MySQL de desarrollo verificados.")
    print("APTO: revisión Alembic 0002_identity_iam.")
    print("APTO: tablas IAM y de Personas presentes en InnoDB; restricciones verificadas.")
    print("APTO: tres roles iniciales; ninguna cuenta ni auditoría creada.")
    print("APTO: existe Persona con id_persona=1 (sin consultar datos personales).")
    print("Comprobación de solo lectura completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
