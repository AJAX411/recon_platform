"""Preflight y comprobación posterior de 0006; exclusivamente lectura MySQL."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from recon_platform.config import obtener_uri_mysql
from verificar_recon_tests_0003 import (_esquema_nuevo as validar_0003,
    _esquema_previo as validar_0002, _identidad as identidad_tests)
from verificar_recon_tests_0004 import TABLAS_0004, validar_0004, validar_destino as destino_tests
from verificar_recon_tests_0005 import NUEVAS as TABLAS_0005, validar_0005, validar_privilegios_migracion
from verificar_recon_dev_0002 import ROLES as ROLES_DEV, verificar_esquema
from verificar_recon_dev_0003 import verificar_sesion_nueva
from verificar_recon_dev_0004 import validar_destino as destino_dev, validar_identidad as identidad_dev

REVISION_ANTERIOR = "0005_puntos_edge_auditoria"
REVISION_NUEVA = "0006_evento_acceso"
TABLAS_ANTERIORES = TABLAS_0004 | TABLAS_0005
PKS = {"tipo_persona": "id_tipo_persona",
       "persona": "id_persona", "rol": "id_rol", "usuario_plataforma": "id_usuario",
       "auditoria_iam": "id_auditoria", "sesion_usuario": "digest",
       "auditoria_personas": "id_auditoria", "punto_acceso": "id_punto_acceso",
       "dispositivo_edge": "id_dispositivo", "evento_auditoria": "id_auditoria"}


def exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise ValueError(mensaje)


def huellas_previas(conexion) -> dict:
    estado = {}
    for tabla, pk in PKS.items():
        resumen = hashlib.sha256()
        total = 0
        for fila in conexion.execute(text(f"SELECT * FROM `{tabla}` ORDER BY `{pk}`")):
            contenido = repr(tuple(fila)).encode("utf-8")
            resumen.update(len(contenido).to_bytes(8, "big"))
            resumen.update(contenido)
            total += 1
        estado[tabla] = {"filas": total, "huella": resumen.hexdigest()}
    return estado


def validar_base_dev(conexion) -> None:
    """Valida 0001–0003 sin exigir que los datos operativos estén vacíos."""
    inspector = inspect(conexion)
    for tabla, pk in (("tipo_persona", "id_tipo_persona"),
                      ("persona", "id_persona")):
        exigir(inspector.get_pk_constraint(tabla)["constrained_columns"] == [pk],
               f"PK de {tabla} inesperada.")
    unicas = {
        tabla: {item["name"]: item["column_names"]
                for item in inspector.get_unique_constraints(tabla)}
        for tabla in ("tipo_persona", "persona")
    }
    exigir(unicas["tipo_persona"].get("uq_tipo_persona_nombre") == ["nombre"],
           "Unicidad de TipoPersona inesperada.")
    exigir(unicas["persona"].get("uq_persona_identificador_institucional")
           == ["identificador_institucional"]
           and unicas["persona"].get("uq_persona_documento")
           == ["tipo_documento", "numero_documento"],
           "Unicidades de Persona inesperadas.")
    relaciones = {fk["name"]: (fk["constrained_columns"], fk["referred_table"],
                                fk["referred_columns"])
                  for fk in inspector.get_foreign_keys("persona")}
    exigir(relaciones == {"fk_persona_tipo_persona":
           (["id_tipo_persona"], "tipo_persona", ["id_tipo_persona"])},
           "FK de Persona inesperada.")
    borrados = dict(conexion.execute(text(
        "SELECT CONSTRAINT_NAME, DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
        "WHERE CONSTRAINT_SCHEMA=DATABASE() AND TABLE_NAME='persona'")).all())
    exigir(borrados == {"fk_persona_tipo_persona": "RESTRICT"},
           "Regla de borrado de Persona inesperada.")

    # Son los validadores usados por los preflight anteriores de recon_dev.
    verificar_esquema(conexion)
    verificar_sesion_nueva(conexion, exigir_vacia=False)
    roles = conexion.execute(text("SELECT nombre FROM rol")).scalars().all()
    exigir(len(roles) == 3 and set(roles) == ROLES_DEV,
           "Catálogo de roles inesperado en recon_dev.")
    exigir(conexion.scalar(text(
        "SELECT COUNT(*) FROM usuario_plataforma u JOIN rol r ON r.id_rol=u.id_rol "
        "WHERE r.nombre='SUPERADMIN'")) == 1,
        "Se exige una sola cuenta SUPERADMIN en recon_dev.")
    exigir(conexion.scalar(text(
        "SELECT COUNT(*) FROM usuario_plataforma u JOIN rol r ON r.id_rol=u.id_rol "
        "WHERE r.nombre='SUPERADMIN' AND u.estado='ACTIVO'")) == 1,
        "Se exige un SUPERADMIN operativo en recon_dev.")


def validar_0006(conexion) -> None:
    inspector = inspect(conexion)
    columnas = {c["name"]: c for c in inspector.get_columns("evento_acceso")}
    nulabilidad = {"id_evento_acceso": False, "id_persona": True,
        "id_punto_acceso": False, "tipo_movimiento": False, "resultado": False,
        "metodo_registro": False, "id_usuario_registrador": True,
        "fecha_hora_ocurrencia": False, "tipo_incidencia_secuencia": True,
        "id_dispositivo": True, "clave_idempotencia": True}
    exigir({n: c["nullable"] for n, c in columnas.items()} == nulabilidad,
           "Columnas de evento_acceso inesperadas.")
    exigir(inspector.get_pk_constraint("evento_acceso")["constrained_columns"] == ["id_evento_acceso"],
           "PK de evento_acceso inesperada.")
    tipos = {r["COLUMN_NAME"]: r for r in conexion.execute(text(
        "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH, "
        "DATETIME_PRECISION, COLLATION_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='evento_acceso'"
    )).mappings()}
    exigir(set(tipos) == set(columnas), "Tipos de evento_acceso incompletos.")
    for nombre in ("id_evento_acceso", "id_persona", "id_punto_acceso",
                   "id_usuario_registrador", "id_dispositivo"):
        exigir(tipos[nombre]["DATA_TYPE"] == "int"
               and "unsigned" in tipos[nombre]["COLUMN_TYPE"].lower(),
               f"Identificador {nombre} incompatible.")
    exigir(tipos["fecha_hora_ocurrencia"]["DATA_TYPE"] == "datetime"
           and tipos["fecha_hora_ocurrencia"]["DATETIME_PRECISION"] == 6,
           "Fecha de evento incompatible.")
    for nombre, longitud in (("tipo_movimiento", 10), ("resultado", 10),
                             ("metodo_registro", 10), ("tipo_incidencia_secuencia", 40)):
        exigir(tipos[nombre]["DATA_TYPE"] == "varchar"
               and tipos[nombre]["CHARACTER_MAXIMUM_LENGTH"] == longitud
               and tipos[nombre]["COLLATION_NAME"] == "utf8mb4_bin",
               f"Tipo o colación de {nombre} incompatible.")
    exigir(tipos["clave_idempotencia"]["DATA_TYPE"] == "char"
           and tipos["clave_idempotencia"]["CHARACTER_MAXIMUM_LENGTH"] == 36
           and tipos["clave_idempotencia"]["COLLATION_NAME"] == "ascii_bin",
           "Clave idempotente incompatible.")
    fks = {f["name"]: (f["constrained_columns"], f["referred_table"], f["referred_columns"])
           for f in inspector.get_foreign_keys("evento_acceso")}
    esperadas = {
        "fk_evento_acceso_persona": (["id_persona"], "persona", ["id_persona"]),
        "fk_evento_acceso_punto": (["id_punto_acceso"], "punto_acceso", ["id_punto_acceso"]),
        "fk_evento_acceso_registrador": (["id_usuario_registrador"], "usuario_plataforma", ["id_usuario"]),
        "fk_evento_acceso_dispositivo": (["id_dispositivo"], "dispositivo_edge", ["id_dispositivo"]),
    }
    exigir(fks == esperadas, "FK de evento_acceso inesperadas.")
    borrados = dict(conexion.execute(text(
        "SELECT CONSTRAINT_NAME, DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
        "WHERE CONSTRAINT_SCHEMA=DATABASE() AND TABLE_NAME='evento_acceso'")).all())
    exigir(borrados == {nombre: "RESTRICT" for nombre in esperadas}, "Regla de borrado inesperada.")
    unicos = {u["name"]: u["column_names"] for u in inspector.get_unique_constraints("evento_acceso")}
    exigir(unicos == {"uq_evento_acceso_clave_idempotencia": ["clave_idempotencia"]},
           "UNIQUE idempotente inesperada.")
    indices = {i["name"]: i["column_names"] for i in inspector.get_indexes("evento_acceso")}
    for nombre, columnas_esperadas in {
        "ix_evento_acceso_secuencia": ["id_persona", "resultado", "fecha_hora_ocurrencia", "id_evento_acceso"],
        "ix_evento_acceso_fecha": ["fecha_hora_ocurrencia", "id_evento_acceso"],
        "ix_evento_acceso_alertas": ["tipo_incidencia_secuencia", "fecha_hora_ocurrencia", "id_evento_acceso"],
        "ix_evento_acceso_punto_fecha": ["id_punto_acceso", "fecha_hora_ocurrencia"],
        "ix_evento_acceso_registrador": ["id_usuario_registrador"],
        "ix_evento_acceso_dispositivo": ["id_dispositivo"],
    }.items():
        exigir(indices.get(nombre) == columnas_esperadas, f"Índice {nombre} ausente.")
    checks = dict(conexion.execute(text(
        "SELECT CONSTRAINT_NAME, ENFORCED FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='evento_acceso' AND CONSTRAINT_TYPE='CHECK'")).all())
    exigir(checks == {nombre: "YES" for nombre in {
        "ck_evento_acceso_movimiento", "ck_evento_acceso_resultado", "ck_evento_acceso_metodo",
        "ck_evento_acceso_incidencia", "ck_evento_acceso_incidencia_autorizada",
        "ck_evento_acceso_manual"}}, "CHECK de 0006 ausentes o no aplicados.")


def verificar(base: str, etapa: str, guardar: Path | None, comparar: Path | None) -> None:
    exigir(base in {"recon_tests", "recon_dev"} and etapa in {"antes", "despues"},
           "Destino o etapa inválidos.")
    exigir(not (guardar and comparar) and (etapa != "despues" or guardar is not None
                                     or comparar is not None),
           "Se exige estado previo o comparación posterior.")
    variables = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_TEST_NAME", "DB_TEST_USER",
                 "DB_TEST_PASSWORD") if base == "recon_tests" else (
                 "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    exigir(all(os.getenv(v) for v in variables), "Configuración explícita incompleta.")
    uri = obtener_uri_mysql(pruebas=base == "recon_tests")
    if uri is None:
        raise ValueError("Configuración explícita incompleta.")
    url = make_url(uri)
    (destino_tests if base == "recon_tests" else destino_dev)(url)
    motor = create_engine(url, poolclass=NullPool)
    try:
        with motor.connect() as conexion:
            (identidad_tests if base == "recon_tests" else identidad_dev)(conexion)
            tablas = {clave: valor for clave, valor in conexion.execute(text(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()")).all()}
            esperadas = TABLAS_ANTERIORES | ({"evento_acceso"} if etapa == "despues" else set())
            exigir(set(tablas) == esperadas and all(v == "InnoDB" for v in tablas.values()),
                   "Tablas o motores inesperados.")
            revision = conexion.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
            exigir(revision == [REVISION_NUEVA if etapa == "despues" else REVISION_ANTERIOR],
                   "Revisión Alembic inesperada.")
            if etapa == "antes":
                validar_privilegios_migracion(conexion, base)
            if base == "recon_tests":
                validar_0002(conexion)
                validar_0003(conexion)
            else:
                validar_base_dev(conexion)
            validar_0004(conexion)
            validar_0005(conexion)
            if base == "recon_tests":
                for tabla in ("persona", "usuario_plataforma", "auditoria_iam",
                              "sesion_usuario", "auditoria_personas", "punto_acceso",
                              "dispositivo_edge", "evento_auditoria"):
                    exigir(conexion.scalar(text(f"SELECT COUNT(*) FROM `{tabla}`")) == 0,
                           "recon_tests contiene datos fuera de los catálogos.")
            if etapa == "despues":
                validar_0006(conexion)
                if base == "recon_tests":
                    exigir(conexion.scalar(text("SELECT COUNT(*) FROM evento_acceso")) == 0,
                           "La tabla nueva contiene eventos inesperados.")
            estado = huellas_previas(conexion)
    finally:
        motor.dispose()
    if guardar is not None:
        exigir(not guardar.exists(), "El estado previo ya existe.")
        guardar.write_text(json.dumps(estado, sort_keys=True), encoding="utf-8")
    if comparar is not None:
        exigir(estado == json.loads(comparar.read_text(encoding="utf-8")),
               "Los datos previos cambiaron durante la migración.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificador read-only 0006")
    parser.add_argument("--base", required=True, choices=("recon_tests", "recon_dev"))
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--antes", action="store_true")
    grupo.add_argument("--despues", action="store_true")
    parser.add_argument("--guardar-estado", type=Path)
    parser.add_argument("--comparar-estado", type=Path)
    args = parser.parse_args()
    try:
        verificar(args.base, "antes" if args.antes else "despues",
                 args.guardar_estado, args.comparar_estado)
    except Exception:
        print("NO APTO: identidad, revisión, esquema, objetos o datos previos inesperados.", file=sys.stderr)
        return 1
    print("APTO: destino y revisión 0006 verificados; consulta de solo lectura.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
