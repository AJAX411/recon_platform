"""Preflight y comprobación posterior de 0005 en recon_tests; solo lectura."""

import argparse
import os
import re
import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.pool import NullPool

from recon_platform.config import obtener_uri_mysql
from verificar_recon_tests_0003 import (
    VerificacionFallida as VerificacionFallida,  # Reexportada para las pruebas del verificador.
    _esquema_nuevo as verificar_0003,
    _esquema_previo as verificar_0002, _identidad, _exigir,
)
from verificar_recon_tests_0004 import TABLAS_0004, validar_0004, validar_destino

REVISION = "0005_puntos_edge_auditoria"
NUEVAS = {"punto_acceso", "dispositivo_edge", "evento_auditoria"}


def validar_privilegios_migracion(conexion: Connection, base: str) -> None:
    """Comprueba concesiones directas mínimas antes de cualquier DDL 0005."""
    grants = [fila[0] for fila in conexion.execute(text("SHOW GRANTS FOR CURRENT_USER()"))]
    permisos: set[str] = set()
    patron = re.compile(r"^GRANT (.+?) ON (\*\.\*|`?" + re.escape(base) +
                        r"`?\.\*) TO .+$", re.IGNORECASE)
    for grant in grants:
        if not isinstance(grant, str) or grant.upper().startswith("REVOKE "):
            raise ValueError("Privilegios de migración no concluyentes.")
        coincidencia = patron.fullmatch(grant)
        if coincidencia:
            permisos.update(p.strip().upper() for p in coincidencia[1].split(","))
    requeridos = {"SELECT", "INSERT", "UPDATE", "CREATE", "INDEX", "REFERENCES"}
    _exigir("ALL PRIVILEGES" in permisos or requeridos <= permisos,
            "La cuenta no acredita permisos directos para migrar 0005.")


def validar_0005(conexion: Connection) -> None:
    inspector = inspect(conexion)
    columnas = {
        "punto_acceso": {"id_punto_acceso": False, "codigo": False, "nombre": False,
                         "descripcion": True, "estado": False, "fecha_creacion": False,
                         "fecha_actualizacion": False},
        "dispositivo_edge": {"id_dispositivo": False, "id_punto_acceso": False,
                             "codigo": False, "nombre": False, "modo_operacion": False,
                             "estado": False, "ultima_comunicacion": True,
                             "fecha_creacion": False, "fecha_actualizacion": False},
        "evento_auditoria": {"id_auditoria": False, "id_usuario_actor": True,
                             "tipo_actor": False, "accion": False, "recurso_tipo": True,
                             "id_recurso_afectado": True, "resultado": False,
                             "detalle": True, "fecha_hora": False},
    }
    primarias = {"punto_acceso": "id_punto_acceso", "dispositivo_edge": "id_dispositivo",
                 "evento_auditoria": "id_auditoria"}
    tipos = {
        "punto_acceso": {"codigo": ("varchar", 20), "nombre": ("varchar", 100),
                         "descripcion": ("varchar", 150), "estado": ("varchar", 20)},
        "dispositivo_edge": {"codigo": ("varchar", 20), "nombre": ("varchar", 100),
                             "modo_operacion": ("varchar", 20), "estado": ("varchar", 20)},
        "evento_auditoria": {"tipo_actor": ("varchar", 20), "accion": ("varchar", 50),
                             "recurso_tipo": ("varchar", 50),
                             "id_recurso_afectado": ("varchar", 100),
                             "resultado": ("varchar", 20)},
    }
    for tabla, esperadas in columnas.items():
        actuales = {c["name"]: c["nullable"] for c in inspector.get_columns(tabla)}
        _exigir(actuales == esperadas, f"Columnas de {tabla} inesperadas.")
        _exigir(inspector.get_pk_constraint(tabla)["constrained_columns"] == [primarias[tabla]],
                f"PK de {tabla} inesperada.")
        metadata = {r["COLUMN_NAME"]: r for r in conexion.execute(text(
            "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH "
            "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=:tabla"
        ), {"tabla": tabla}).mappings()}
        _exigir(set(metadata) == set(esperadas), f"Metadatos de {tabla} incompletos.")
        for nombre, esperado in tipos[tabla].items():
            _exigir((metadata[nombre]["DATA_TYPE"], metadata[nombre]["CHARACTER_MAXIMUM_LENGTH"])
                    == esperado, f"Tipo de {tabla}.{nombre} inesperado.")
        for nombre in esperadas:
            if nombre.startswith("id_") and nombre != "id_recurso_afectado":
                _exigir(metadata[nombre]["DATA_TYPE"] == "int" and
                        "unsigned" in metadata[nombre]["COLUMN_TYPE"].lower(),
                        f"Identificador de {tabla} incompatible.")
            if nombre.startswith("fecha_") or nombre == "ultima_comunicacion":
                _exigir(metadata[nombre]["DATA_TYPE"] == "datetime",
                        f"Fecha de {tabla} incompatible.")
        if tabla == "evento_auditoria":
            _exigir(metadata["detalle"]["DATA_TYPE"] == "text", "Detalle de auditoría incompatible.")
    for tabla, unico in (("punto_acceso", "uq_punto_acceso_codigo"),
                         ("dispositivo_edge", "uq_dispositivo_edge_codigo")):
        _exigir({u["name"]: u["column_names"] for u in inspector.get_unique_constraints(tabla)}
                == {unico: ["codigo"]}, f"Unicidad de {tabla} inesperada.")
    relaciones = {
        "dispositivo_edge": {"fk_dispositivo_edge_punto": (["id_punto_acceso"], "punto_acceso", ["id_punto_acceso"])},
        "evento_auditoria": {"fk_evento_auditoria_actor": (["id_usuario_actor"], "usuario_plataforma", ["id_usuario"])},
    }
    for tabla, esperado in relaciones.items():
        actual = {f["name"]: (f["constrained_columns"], f["referred_table"], f["referred_columns"])
                  for f in inspector.get_foreign_keys(tabla)}
        _exigir(actual == esperado, f"FK de {tabla} inesperada.")
        borrados = dict(conexion.execute(text(
            "SELECT CONSTRAINT_NAME, DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA=DATABASE() AND TABLE_NAME=:tabla"
        ), {"tabla": tabla}).all())
        _exigir(borrados == {nombre: "RESTRICT" for nombre in esperado},
                f"Borrado referencial de {tabla} inesperado.")
    checks = dict(conexion.execute(text(
        "SELECT tc.CONSTRAINT_NAME, tc.ENFORCED FROM information_schema.TABLE_CONSTRAINTS tc "
        "WHERE tc.TABLE_SCHEMA=DATABASE() AND tc.TABLE_NAME IN "
        "('punto_acceso','dispositivo_edge','evento_auditoria') AND tc.CONSTRAINT_TYPE='CHECK'"
    )).all())
    _exigir(checks == {nombre: "YES" for nombre in {
        "ck_punto_acceso_estado", "ck_dispositivo_edge_estado", "ck_dispositivo_edge_modo",
        "ck_evento_auditoria_tipo_actor", "ck_evento_auditoria_resultado",
        "ck_evento_auditoria_actor"}}, "CHECK de 0005 ausentes o no aplicados.")
    indices = {
        "punto_acceso": {"ix_punto_acceso_estado": ["estado"]},
        "dispositivo_edge": {"ix_dispositivo_edge_id_punto_acceso": ["id_punto_acceso"],
                             "ix_dispositivo_edge_estado": ["estado"]},
        "evento_auditoria": {"ix_evento_auditoria_id_usuario_actor": ["id_usuario_actor"],
                             "ix_evento_auditoria_accion": ["accion"],
                             "ix_evento_auditoria_fecha_hora": ["fecha_hora"],
                             "ix_evento_auditoria_recurso": ["recurso_tipo", "id_recurso_afectado"]},
    }
    for tabla, esperados in indices.items():
        actuales = {i["name"]: i["column_names"] for i in inspector.get_indexes(tabla)}
        _exigir(all(actuales.get(nombre) == columnas for nombre, columnas in esperados.items()),
                f"Índices de {tabla} incompletos.")


def verificar(etapa: str) -> None:
    _exigir(etapa in {"antes", "despues"}, "Etapa inválida.")
    _exigir(all(os.getenv(n) for n in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_TEST_NAME",
                                      "DB_TEST_USER", "DB_TEST_PASSWORD")),
            "Falta configuración explícita de recon_tests.")
    url = make_url(obtener_uri_mysql(pruebas=True))
    validar_destino(url)
    motor = create_engine(url, poolclass=NullPool)
    try:
        with motor.connect() as conexion:
            _identidad(conexion)
            tablas = dict(conexion.execute(text(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()"
            )).all())
            esperadas = TABLAS_0004 | (NUEVAS if etapa == "despues" else set())
            _exigir(set(tablas) == esperadas and all(m == "InnoDB" for m in tablas.values()),
                    "Tablas o motores inesperados.")
            _exigir(conexion.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
                    == [REVISION if etapa == "despues" else "0004_auditoria_personas"],
                    "Revisión Alembic inesperada.")
            if etapa == "antes":
                validar_privilegios_migracion(conexion, "recon_tests")
            verificar_0002(conexion)
            verificar_0003(conexion)
            validar_0004(conexion)
            _exigir(conexion.scalar(text("SELECT COUNT(*) FROM auditoria_personas")) == 0,
                    "Hay residuos de auditoría de Personas en recon_tests.")
            if etapa == "despues":
                validar_0005(conexion)
                _exigir(all(conexion.scalar(text(f"SELECT COUNT(*) FROM `{tabla}`")) == 0
                            for tabla in NUEVAS), "Hay residuos en tablas 0005 de pruebas.")
    finally:
        motor.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificación read-only de 0005 en recon_tests.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--antes", action="store_true")
    grupo.add_argument("--despues", action="store_true")
    args = parser.parse_args()
    try:
        verificar("antes" if args.antes else "despues")
    except Exception:
        print("NO APTO: identidad, revisión, esquema o residuos de recon_tests inesperados.", file=sys.stderr)
        return 1
    print("APTO: recon_tests y esquema 0005 verificados; solo lectura.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
