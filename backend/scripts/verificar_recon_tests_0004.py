"""Verificación de solo lectura de recon_tests antes/después de 0004.

Nunca aplica migraciones ni modifica datos. No imprime URL ni credenciales.
"""

import argparse
import os
import re
import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.pool import NullPool

from recon_platform.config import obtener_uri_mysql
from verificar_recon_tests_0003 import (
    TABLAS_0002, VerificacionFallida, _esquema_nuevo as verificar_0003,
    _esquema_previo as verificar_0002, _identidad, _exigir,
)

REVISIONES = {"antes": "0003_sesiones_iam", "despues": "0004_auditoria_personas"}
TABLAS_0003 = TABLAS_0002 | {"sesion_usuario"}
TABLAS_0004 = TABLAS_0003 | {"auditoria_personas"}
TIPOS_PERSONA = {"ESTUDIANTE", "DOCENTE", "ADMINISTRATIVO", "SERVICIOS_GENERALES",
                 "VISITANTE", "PERSONAL_SEGURIDAD"}
ACCIONES = {"REGISTRAR_PERSONA", "ACTUALIZAR_PERSONA", "ACTIVAR_PERSONA",
            "DESACTIVAR_PERSONA"}


def validar_destino(url) -> None:
    _exigir(
        url.drivername == "mysql+pymysql"
        and (url.host, url.port, url.database, url.username)
        == ("127.0.0.1", 3306, "recon_tests", "recon_test_app")
        and os.getenv("DB_NAME") == "recon_dev",
        "Se exige recon_tests/recon_test_app local y DB_NAME=recon_dev.",
    )


def validar_0004(conexion: Connection) -> None:
    inspector = inspect(conexion)
    columnas = {item["name"]: item for item in inspector.get_columns("auditoria_personas")}
    esperadas = {"id_auditoria", "actor_id", "id_persona", "accion", "fecha"}
    _exigir(set(columnas) == esperadas and all(not c["nullable"] for c in columnas.values()),
            "Columnas o nulabilidad de auditoria_personas inesperadas.")
    _exigir(inspector.get_pk_constraint("auditoria_personas")["constrained_columns"]
            == ["id_auditoria"], "PK de auditoria_personas inesperada.")
    tipos = {fila["COLUMN_NAME"]: fila for fila in conexion.execute(text(
        "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH "
        "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'auditoria_personas'"
    )).mappings()}
    _exigir(set(tipos) == esperadas, "Metadatos de columnas incompletos.")
    _exigir(all(tipos[n]["DATA_TYPE"] == "int" and
                "unsigned" in tipos[n]["COLUMN_TYPE"].lower()
                for n in ("id_auditoria", "actor_id", "id_persona")),
            "Los identificadores deben ser INT UNSIGNED.")
    _exigir(tipos["accion"]["DATA_TYPE"] == "varchar"
            and tipos["accion"]["CHARACTER_MAXIMUM_LENGTH"] == 30
            and tipos["fecha"]["DATA_TYPE"] == "datetime",
            "Los tipos de acción o fecha no coinciden con 0004.")
    relaciones = {fk["name"]: (fk["constrained_columns"], fk["referred_table"],
                              fk["referred_columns"])
                  for fk in inspector.get_foreign_keys("auditoria_personas")}
    _exigir(relaciones == {
        "fk_auditoria_personas_actor": (["actor_id"], "usuario_plataforma", ["id_usuario"]),
        "fk_auditoria_personas_persona": (["id_persona"], "persona", ["id_persona"]),
    }, "Las FK de auditoria_personas no coinciden con 0004.")
    borrados = {clave: valor for clave, valor in conexion.execute(text(
        "SELECT CONSTRAINT_NAME, DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
        "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'auditoria_personas'"
    )).all()}
    _exigir(borrados == {nombre: "RESTRICT" for nombre in relaciones},
            "La política de borrado de auditoria_personas no coincide con 0004.")
    indices = {indice["name"]: indice["column_names"]
               for indice in inspector.get_indexes("auditoria_personas")}
    _exigir(indices.get("ix_auditoria_personas_id_persona") == ["id_persona"],
            "Falta el índice de auditoría por Persona.")
    _exigir(any(columnas and columnas[0] == "actor_id" for columnas in indices.values()),
            "Falta el índice requerido por la FK del actor.")
    _exigir(not inspector.get_unique_constraints("auditoria_personas"),
            "Auditoría contiene unicidades no previstas.")
    checks = list(conexion.execute(text(
        "SELECT cc.CONSTRAINT_NAME, cc.CHECK_CLAUSE, tc.ENFORCED "
        "FROM information_schema.CHECK_CONSTRAINTS cc "
        "JOIN information_schema.TABLE_CONSTRAINTS tc "
        "ON tc.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA "
        "AND tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME "
        "WHERE tc.TABLE_SCHEMA = DATABASE() AND tc.TABLE_NAME = 'auditoria_personas' "
        "AND tc.CONSTRAINT_TYPE = 'CHECK'"
    )))
    acciones_check = (re.findall(r"(?:_utf8mb4)?\\?'([^'\\]+)\\?'", checks[0][1])
                      if len(checks) == 1 else [])
    _exigir(len(checks) == 1 and checks[0][0] == "ck_auditoria_personas_accion"
            and checks[0][2] == "YES"
            and " in " in checks[0][1].lower()
            and len(acciones_check) == len(ACCIONES)
            and set(acciones_check) == ACCIONES,
            "El CHECK de acciones de auditoría no coincide con 0004.")


def verificar(etapa: str) -> None:
    _exigir(etapa in REVISIONES, "Etapa inválida.")
    requeridas = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_TEST_NAME",
                 "DB_TEST_USER", "DB_TEST_PASSWORD")
    _exigir(all(os.getenv(nombre) for nombre in requeridas),
            "Falta configuración explícita de MySQL de pruebas.")
    uri = obtener_uri_mysql(pruebas=True)
    if uri is None:
        raise VerificacionFallida("Falta configuración explícita de MySQL de pruebas.")
    url = make_url(uri)
    validar_destino(url)
    motor = create_engine(url, poolclass=NullPool)
    try:
        with motor.connect() as conexion:
            _identidad(conexion)
            tablas = {clave: valor for clave, valor in conexion.execute(text(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE()"
            )).all()}
            esperadas = TABLAS_0003 if etapa == "antes" else TABLAS_0004
            _exigir(set(tablas) == esperadas and all(valor == "InnoDB" for valor in tablas.values()),
                    "Tablas o motores del esquema inesperados.")
            _exigir(conexion.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
                    == [REVISIONES[etapa]], "La revisión Alembic no corresponde a la etapa.")
            verificar_0002(conexion)
            verificar_0003(conexion)
            _exigir(set(conexion.execute(text("SELECT nombre FROM tipo_persona")).scalars())
                    == TIPOS_PERSONA, "El catálogo de TipoPersona no coincide.")
            if etapa == "despues":
                validar_0004(conexion)
                _exigir(conexion.scalar(text("SELECT COUNT(*) FROM auditoria_personas")) == 0,
                        "Hay residuos de auditoría de Personas.")
    finally:
        motor.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificación de solo lectura para 0004 en recon_tests.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--antes", action="store_true")
    grupo.add_argument("--despues", action="store_true")
    argumentos = parser.parse_args()
    try:
        verificar("antes" if argumentos.antes else "despues")
    except VerificacionFallida as error:
        print(f"NO APTO: {error}", file=sys.stderr)
        return 1
    except Exception:
        print("NO APTO: no se pudo verificar MySQL de pruebas de forma segura.", file=sys.stderr)
        return 1
    print("APTO: identidad real, revisión, esquema, restricciones y ausencia de residuos verificados.")
    print("Verificación exclusivamente de lectura completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
