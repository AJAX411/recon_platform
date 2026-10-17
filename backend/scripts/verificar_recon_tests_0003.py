"""Barrera de solo lectura para la migración 0003 en recon_tests."""

import argparse
import os
import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.pool import NullPool

from recon_platform.config import obtener_uri_mysql


class VerificacionFallida(Exception):
    """Una condición requerida no se cumple; el detalle es seguro para mostrar."""


TABLAS_0002 = {
    "alembic_version", "tipo_persona", "persona", "rol",
    "usuario_plataforma", "auditoria_iam",
}
ROLES = {"SUPERADMIN", "ADMINISTRADOR", "OPERADOR"}


def _exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise VerificacionFallida(mensaje)


def _identidad(conexion: Connection) -> None:
    base, cuenta, usuario, puerto = conexion.execute(
        text("SELECT DATABASE(), CURRENT_USER(), USER(), @@port")
    ).one()
    _exigir(
        base == "recon_tests"
        and isinstance(cuenta, str) and cuenta.partition("@")[0] == "recon_test_app"
        and isinstance(usuario, str) and usuario.partition("@")[0] == "recon_test_app"
        and puerto == 3306,
        "La identidad real de MySQL no corresponde a recon_tests/recon_test_app.",
    )


def _esquema_previo(conexion: Connection) -> None:
    inspector = inspect(conexion)
    for tabla, clave in (
        ("tipo_persona", "id_tipo_persona"), ("persona", "id_persona"),
        ("rol", "id_rol"), ("usuario_plataforma", "id_usuario"),
        ("auditoria_iam", "id_auditoria"),
    ):
        _exigir(inspector.get_pk_constraint(tabla)["constrained_columns"] == [clave],
                "Una clave primaria anterior no coincide con las migraciones aplicadas.")
    unicas = {
        tabla: {item["name"] for item in inspector.get_unique_constraints(tabla)}
        for tabla in ("tipo_persona", "persona", "rol", "usuario_plataforma")
    }
    _exigir("uq_tipo_persona_nombre" in unicas["tipo_persona"], "Falta UNIQUE de TipoPersona.")
    _exigir(
        {"uq_persona_identificador_institucional", "uq_persona_documento"}
        <= unicas["persona"], "Faltan restricciones UNIQUE de Persona.",
    )
    _exigir("uq_rol_nombre" in unicas["rol"], "Falta UNIQUE de Rol.")
    _exigir("uq_usuario_plataforma_login" in unicas["usuario_plataforma"],
            "Falta UNIQUE de UsuarioPlataforma.")
    relaciones = {
        tabla: {item["name"]: item["referred_table"]
                for item in inspector.get_foreign_keys(tabla)}
        for tabla in ("persona", "usuario_plataforma", "auditoria_iam")
    }
    _exigir(relaciones["persona"] == {"fk_persona_tipo_persona": "tipo_persona"},
            "La FK de Persona no coincide con 0001.")
    _exigir(relaciones["usuario_plataforma"] == {"fk_usuario_plataforma_rol": "rol"},
            "La FK de UsuarioPlataforma no coincide con 0002.")
    _exigir(relaciones["auditoria_iam"] == {
        "fk_auditoria_iam_actor": "usuario_plataforma",
        "fk_auditoria_iam_usuario": "usuario_plataforma",
    }, "Las FK de auditoría IAM no coinciden con 0002.")
    checks = set(conexion.execute(text(
        "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA = DATABASE() AND CONSTRAINT_TYPE = 'CHECK' "
        "AND TABLE_NAME IN ('rol', 'usuario_plataforma')"
    )).scalars())
    _exigir({"ck_rol_nombre_aprobado", "ck_usuario_plataforma_estado"} <= checks,
            "Faltan restricciones CHECK de IAM.")
    nombres = set(conexion.execute(text("SELECT nombre FROM rol")).scalars())
    _exigir(nombres == ROLES, "El catálogo de roles no contiene exactamente los tres roles aprobados.")
    for tabla in ("persona", "usuario_plataforma", "auditoria_iam"):
        cantidad = conexion.scalar(text(f"SELECT COUNT(*) FROM {tabla}"))
        _exigir(cantidad == 0, "La base de pruebas contiene registros operativos previos.")


def _esquema_nuevo(conexion: Connection) -> None:
    inspector = inspect(conexion)
    columnas = {columna["name"]: columna for columna in inspector.get_columns("sesion_usuario")}
    _exigir(set(columnas) == {
        "digest", "id_usuario", "fecha_creacion", "fecha_actividad",
        "fecha_expiracion", "fecha_revocacion",
    }, "Las columnas de sesión no coinciden con 0003.")
    _exigir({nombre for nombre, columna in columnas.items() if columna["nullable"]} == {
        "id_usuario", "fecha_revocacion",
    }, "La obligatoriedad de columnas de sesión no coincide con 0003.")
    tipos = {fila["COLUMN_NAME"]: fila for fila in conexion.execute(text(
        "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH "
        "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'sesion_usuario'"
    )).mappings()}
    _exigir(tipos["digest"]["DATA_TYPE"] == "varchar"
            and tipos["digest"]["CHARACTER_MAXIMUM_LENGTH"] == 64,
            "El tipo de digest no coincide con 0003.")
    _exigir(tipos["id_usuario"]["DATA_TYPE"] == "int"
            and "unsigned" in tipos["id_usuario"]["COLUMN_TYPE"],
            "El tipo de id_usuario no coincide con 0003.")
    _exigir(all(tipos[nombre]["DATA_TYPE"] == "datetime" for nombre in (
        "fecha_creacion", "fecha_actividad", "fecha_expiracion", "fecha_revocacion"
    )), "Los tipos de fechas no coinciden con 0003.")
    _exigir(inspector.get_pk_constraint("sesion_usuario")["constrained_columns"] == ["digest"],
            "La clave primaria de sesión no coincide con 0003.")
    relaciones = {fk["name"]: (fk["constrained_columns"], fk["referred_table"],
                               fk["referred_columns"])
                 for fk in inspector.get_foreign_keys("sesion_usuario")}
    _exigir(relaciones == {"fk_sesion_usuario_cuenta":
            (["id_usuario"], "usuario_plataforma", ["id_usuario"])},
            "La FK de sesión no coincide con 0003.")
    indices = {indice["name"]: indice["column_names"]
               for indice in inspector.get_indexes("sesion_usuario")}
    _exigir(indices.get("ix_sesion_usuario_id_usuario") == ["id_usuario"],
            "Falta el índice de sesiones por cuenta.")
    _exigir(conexion.scalar(text("SELECT COUNT(*) FROM sesion_usuario")) == 0,
            "La tabla de sesiones contiene registros; revisar antes de continuar.")


def verificar(etapa: str) -> None:
    requeridas = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_TEST_NAME",
                 "DB_TEST_USER", "DB_TEST_PASSWORD")
    ausentes = [nombre for nombre in requeridas if not os.getenv(nombre)]
    _exigir(not ausentes, "Faltan variables de entorno: " + ", ".join(ausentes) + ".")
    uri = obtener_uri_mysql(pruebas=True)
    if uri is None:
        raise VerificacionFallida("La configuración de pruebas está incompleta.")
    url = make_url(uri)
    _exigir(
        url.drivername == "mysql+pymysql"
        and (url.host, url.port, url.database, url.username)
        == ("127.0.0.1", 3306, "recon_tests", "recon_test_app"),
        "El destino configurado no es el MySQL de pruebas autorizado.",
    )
    motor = create_engine(url, poolclass=NullPool)
    try:
        with motor.connect() as conexion:
            _identidad(conexion)
            tablas: dict[str, str] = {}
            for fila in conexion.execute(text(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE()"
            )).mappings():
                nombre, motor_tabla = fila["TABLE_NAME"], fila["ENGINE"]
                if isinstance(nombre, str) and isinstance(motor_tabla, str):
                    tablas[nombre] = motor_tabla
            esperadas = TABLAS_0002 | ({"sesion_usuario"} if etapa == "despues" else set())
            _exigir(esperadas <= tablas.keys(), "Faltan tablas requeridas del esquema.")
            _exigir(all(tablas[tabla] == "InnoDB" for tabla in esperadas),
                    "Las tablas requeridas deben usar InnoDB.")
            _exigir(("sesion_usuario" in tablas) == (etapa == "despues"),
                    "La presencia de sesion_usuario no corresponde a la etapa.")
            revision = "0002_identity_iam" if etapa == "antes" else "0003_sesiones_iam"
            _exigir(conexion.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
                    == [revision], "La revisión Alembic no corresponde a la etapa.")
            _esquema_previo(conexion)
            if etapa == "despues":
                _esquema_nuevo(conexion)
    finally:
        motor.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificación de solo lectura de recon_tests.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--antes", action="store_true")
    grupo.add_argument("--despues", action="store_true")
    argumentos = parser.parse_args()
    etapa = "antes" if argumentos.antes else "despues"
    try:
        verificar(etapa)
    except VerificacionFallida as error:
        print(f"NO APTO: {error}", file=sys.stderr)
        return 1
    except Exception:
        print("NO APTO: no se pudo verificar MySQL de pruebas de forma segura.", file=sys.stderr)
        return 1
    print("APTO: destino real recon_tests/recon_test_app y revisión Alembic verificados.")
    print("APTO: esquema de Personas e IAM previo, restricciones y roles verificados.")
    print("APTO: estructura de sesión y ausencia de datos temporales verificadas."
          if etapa == "despues" else "APTO: sesion_usuario aún no existe.")
    print("Verificación exclusivamente de lectura completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
