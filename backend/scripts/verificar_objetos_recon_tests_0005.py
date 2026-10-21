"""Verifica con cuenta visible que recon_tests no tenga objetos omitidos del respaldo."""

import os
import re
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool


def visibilidad_suficiente(grants: list[str]) -> bool:
    globales: set[str] = set()
    esquema: set[str] = set()
    patron = re.compile(r"^GRANT (.+?) ON (\*\.\*|`?recon_tests`?\.\*) TO .+$", re.IGNORECASE)
    for grant in grants:
        if not isinstance(grant, str) or grant.upper().startswith("REVOKE "):
            return False
        coincide = patron.fullmatch(grant)
        if coincide:
            (globales if coincide[2] == "*.*" else esquema).update(
                valor.strip().upper() for valor in coincide[1].split(","))
    return bool({"ALL PRIVILEGES", "SELECT", "SHOW_ROUTINE"} & globales
                and {"ALL PRIVILEGES", "EVENT"} & (globales | esquema)
                and {"ALL PRIVILEGES", "TRIGGER"} & (globales | esquema))


def verificar() -> None:
    usuario = os.getenv("RECON_BACKUP_ADMIN_USER", "")
    clave = os.getenv("RECON_BACKUP_ADMIN_PASSWORD", "")
    if not usuario or usuario in {"recon_test_app", "recon_dev_app"} or not clave:
        raise ValueError("Se exige cuenta administrativa independiente.")
    url = URL.create("mysql+pymysql", username=usuario, password=clave,
                     host="127.0.0.1", port=3306, database="recon_tests",
                     query={"charset": "utf8mb4"})
    motor = create_engine(url, poolclass=NullPool)
    try:
        with motor.connect() as conexion:
            base, cuenta, usuario_real, puerto = conexion.execute(text(
                "SELECT DATABASE(), CURRENT_USER(), USER(), @@port"
            )).one()
            if (base != "recon_tests" or puerto != 3306
                or cuenta.partition("@")[0] != usuario
                or usuario_real.partition("@")[0] != usuario):
                raise ValueError("Identidad administrativa inesperada.")
            grants = [fila[0] for fila in conexion.execute(text("SHOW GRANTS FOR CURRENT_USER()"))]
            if not visibilidad_suficiente(grants):
                raise ValueError("Visibilidad de objetos incompleta.")
            for nombre, columna in (("EVENTS", "EVENT_SCHEMA"),
                                    ("ROUTINES", "ROUTINE_SCHEMA"),
                                    ("TRIGGERS", "TRIGGER_SCHEMA")):
                cantidad = conexion.scalar(text(
                    f"SELECT COUNT(*) FROM information_schema.{nombre} WHERE {columna}='recon_tests'"
                ))
                if type(cantidad) is not int or cantidad != 0:
                    raise ValueError("Existen objetos fuera del respaldo de tablas.")
    finally:
        motor.dispose()


def main() -> int:
    if len(sys.argv) != 1:
        print("NO APTO: no se aceptan argumentos.", file=sys.stderr)
        return 1
    try:
        verificar()
    except Exception:
        print("NO APTO: no se pudo acreditar visibilidad y ausencia de objetos en recon_tests.",
              file=sys.stderr)
        return 1
    print("APTO: cero eventos, rutinas y triggers con visibilidad completa en recon_tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
