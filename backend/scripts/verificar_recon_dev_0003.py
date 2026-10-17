"""Verificación de solo lectura antes o después de 0003 en recon_dev."""

import argparse
import os
import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.pool import NullPool

from recon_platform.config import obtener_uri_mysql
from verificar_recon_dev_0002 import (
    DESTINO, ROLES, TABLAS, VARIABLES, VerificacionFallida, verificar_esquema,
)


def exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise VerificacionFallida(mensaje)


def verificar_datos_previos(conexion: Connection) -> None:
    inspector = inspect(conexion)
    unicas = {
        tabla: {unica["name"]: unica["column_names"]
                for unica in inspector.get_unique_constraints(tabla)}
        for tabla in ("tipo_persona", "persona")
    }
    exigir(unicas["tipo_persona"].get("uq_tipo_persona_nombre") == ["nombre"],
           "La unicidad de TipoPersona no coincide con 0001.")
    exigir(unicas["persona"].get("uq_persona_identificador_institucional")
           == ["identificador_institucional"]
           and unicas["persona"].get("uq_persona_documento")
           == ["tipo_documento", "numero_documento"],
           "Las unicidades de Persona no coinciden con 0001.")
    fks_persona = {fk["name"]: (fk["constrained_columns"], fk["referred_table"],
                               fk["referred_columns"])
                   for fk in inspector.get_foreign_keys("persona")}
    exigir(fks_persona == {"fk_persona_tipo_persona":
           (["id_tipo_persona"], "tipo_persona", ["id_tipo_persona"])},
           "La FK de Persona no coincide con 0001.")
    exigir(conexion.scalar(text(
        "SELECT 1 FROM persona WHERE id_persona = 1 LIMIT 1"
    )) == 1, "No se conserva la Persona id_persona=1.")

    roles = conexion.execute(text("SELECT nombre FROM rol")).scalars().all()
    exigir(len(roles) == 3 and set(roles) == ROLES, "El catálogo de roles es inesperado.")
    exigir(conexion.scalar(text("SELECT COUNT(*) FROM usuario_plataforma")) == 1,
           "Se exige exactamente una cuenta de plataforma en desarrollo.")
    cuenta = conexion.execute(text(
        "SELECT u.id_usuario, u.estado, r.nombre AS rol_nombre, "
        "u.hash_contrasena LIKE 'scrypt:%' AS hash_scrypt "
        "FROM usuario_plataforma AS u JOIN rol AS r ON r.id_rol = u.id_rol"
    )).mappings().one_or_none()
    if cuenta is None:
        raise VerificacionFallida("No se encontró la cuenta SUPERADMIN inicial.")
    exigir(cuenta["estado"] == "ACTIVO"
           and cuenta["rol_nombre"] == "SUPERADMIN" and cuenta["hash_scrypt"] == 1,
           "La cuenta inicial no es un SUPERADMIN activo con hash seguro.")
    auditorias = conexion.execute(text(
        "SELECT actor_id, usuario_id, accion, resultado, anterior, nuevo "
        "FROM auditoria_iam"
    )).mappings().all()
    exigir(len(auditorias) == 1, "Se exige exactamente la auditoría de bootstrap.")
    auditoria = auditorias[0]
    exigir(auditoria["actor_id"] is None
           and auditoria["usuario_id"] == cuenta["id_usuario"]
           and auditoria["accion"] == "BOOTSTRAP_SUPERADMIN"
           and auditoria["resultado"] == "EXITO"
           and auditoria["anterior"] is None and auditoria["nuevo"] is None,
           "La auditoría de bootstrap no coincide con la cuenta inicial.")


def verificar_sesion_nueva(conexion: Connection, *, exigir_vacia: bool = True) -> None:
    inspector = inspect(conexion)
    columnas = {columna["name"]: columna for columna in inspector.get_columns("sesion_usuario")}
    exigir(set(columnas) == {
        "digest", "id_usuario", "fecha_creacion", "fecha_actividad",
        "fecha_expiracion", "fecha_revocacion",
    }, "Las columnas de sesión no coinciden con 0003.")
    exigir({nombre for nombre, columna in columnas.items() if columna["nullable"]}
           == {"id_usuario", "fecha_revocacion"},
           "La nulabilidad de sesión no coincide con 0003.")
    exigir(inspector.get_pk_constraint("sesion_usuario")["constrained_columns"]
           == ["digest"], "La clave primaria de sesión no coincide con 0003.")
    tipos = {fila["COLUMN_NAME"]: fila for fila in conexion.execute(text(
        "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH "
        "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'sesion_usuario'"
    )).mappings()}
    exigir(tipos["digest"]["DATA_TYPE"] == "varchar"
           and tipos["digest"]["CHARACTER_MAXIMUM_LENGTH"] == 64,
           "El tipo de digest no coincide con 0003.")
    exigir(tipos["id_usuario"]["DATA_TYPE"] == "int"
           and "unsigned" in tipos["id_usuario"]["COLUMN_TYPE"],
           "El tipo de id_usuario no coincide con 0003.")
    exigir(all(tipos[nombre]["DATA_TYPE"] == "datetime" for nombre in (
        "fecha_creacion", "fecha_actividad", "fecha_expiracion", "fecha_revocacion"
    )), "Los tipos de fechas no coinciden con 0003.")
    relaciones = {fk["name"]: (fk["constrained_columns"], fk["referred_table"],
                               fk["referred_columns"])
                 for fk in inspector.get_foreign_keys("sesion_usuario")}
    exigir(relaciones == {"fk_sesion_usuario_cuenta":
           (["id_usuario"], "usuario_plataforma", ["id_usuario"])},
           "La FK de sesión no coincide con 0003.")
    indices = {indice["name"]: indice["column_names"]
               for indice in inspector.get_indexes("sesion_usuario")}
    exigir(indices.get("ix_sesion_usuario_id_usuario") == ["id_usuario"],
           "Falta el índice de sesión por cuenta.")
    if exigir_vacia:
        exigir(conexion.scalar(text("SELECT COUNT(*) FROM sesion_usuario")) == 0,
               "La nueva tabla de sesiones debe estar vacía tras la migración.")


def verificar(etapa: str) -> None:
    ausentes = [nombre for nombre in VARIABLES if not os.getenv(nombre)]
    exigir(not ausentes, "Faltan variables de entorno: " + ", ".join(ausentes) + ".")
    uri = obtener_uri_mysql(pruebas=False)
    if uri is None:
        raise VerificacionFallida("La configuración MySQL de desarrollo está incompleta.")
    url = make_url(uri)
    exigir(url.drivername == "mysql+pymysql"
           and (url.host, url.port, url.database, url.username) == DESTINO,
           "El destino configurado no es recon_dev con recon_dev_app.")
    motor = create_engine(url, poolclass=NullPool)
    try:
        with motor.connect() as conexion:
            base, cuenta, usuario, puerto = conexion.execute(text(
                "SELECT DATABASE(), CURRENT_USER(), USER(), @@port"
            )).one()
            exigir(base == "recon_dev" and isinstance(cuenta, str)
                   and cuenta.partition("@")[0] == "recon_dev_app"
                   and isinstance(usuario, str)
                   and usuario.partition("@")[0] == "recon_dev_app"
                   and puerto == 3306,
                   "La identidad real de MySQL no corresponde a recon_dev.")
            tablas: dict[str, str] = {}
            for fila in conexion.execute(text(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE()"
            )).mappings():
                nombre, motor_tabla = fila["TABLE_NAME"], fila["ENGINE"]
                if isinstance(nombre, str) and isinstance(motor_tabla, str):
                    tablas[nombre] = motor_tabla
            esperadas = TABLAS | ({"sesion_usuario"} if etapa == "despues" else set())
            exigir(esperadas <= tablas.keys(), "Faltan tablas previas requeridas.")
            exigir(all(tablas[tabla] == "InnoDB" for tabla in esperadas),
                   "Las tablas requeridas deben usar InnoDB.")
            exigir(("sesion_usuario" in tablas) == (etapa == "despues"),
                   "La presencia de sesion_usuario no corresponde a la etapa.")
            revision = "0002_identity_iam" if etapa == "antes" else "0003_sesiones_iam"
            exigir(conexion.execute(text(
                "SELECT version_num FROM alembic_version"
            )).scalars().all() == [revision],
                   "La revisión Alembic no corresponde a la etapa.")
            verificar_esquema(conexion)
            verificar_datos_previos(conexion)
            if etapa == "despues":
                verificar_sesion_nueva(conexion)
    finally:
        motor.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificación de solo lectura de recon_dev.")
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
        print("NO APTO: no se pudo verificar MySQL de desarrollo de forma segura.",
              file=sys.stderr)
        return 1
    print("APTO: conexión real recon_dev/recon_dev_app y revisión Alembic verificadas.")
    print("APTO: esquema anterior, roles y Persona id_persona=1 conservados.")
    print("APTO: único SUPERADMIN activo y su auditoría de bootstrap conservados.")
    print("APTO: nueva tabla de sesiones comprobada y vacía."
          if etapa == "despues" else "APTO: la tabla de sesiones aún no existe.")
    print("Verificación exclusivamente de lectura completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
