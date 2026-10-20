"""Comprobación administrativa de solo lectura antes del respaldo de 0004.

Una lista vacía de INFORMATION_SCHEMA solo se acepta tras acreditar visibilidad.
"""

import os
import re
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool


class VerificacionFallida(Exception):
    """Impide omitir objetos almacenados de un respaldo incompleto."""


def privilegios_suficientes(grants: list[str]) -> bool:
    """Exige concesiones directas; las heredadas de roles fallan cerradas."""
    globales: set[str] = set()
    esquema: set[str] = set()
    patron = re.compile(
        r"^GRANT (.+?) ON (\*\.\*|`?recon_dev`?\.\*) TO .+$", re.IGNORECASE
    )
    for sentencia in grants:
        # Un REVOKE parcial puede anular privilegios globales en esta base.
        if sentencia.upper().startswith("REVOKE "):
            return False
        coincidencia = patron.fullmatch(sentencia)
        if coincidencia is None:
            continue
        privilegios = {valor.strip().upper() for valor in coincidencia[1].split(",")}
        if coincidencia[2] == "*.*":
            globales.update(privilegios)
        else:
            esquema.update(privilegios)
    visible_rutinas = bool({"ALL PRIVILEGES", "SELECT", "SHOW_ROUTINE"} & globales)
    visible_eventos = ("ALL PRIVILEGES" in globales or "EVENT" in globales
                       or "ALL PRIVILEGES" in esquema or "EVENT" in esquema)
    visible_triggers = ("ALL PRIVILEGES" in globales or "TRIGGER" in globales
                        or "ALL PRIVILEGES" in esquema or "TRIGGER" in esquema)
    return visible_rutinas and visible_eventos and visible_triggers


def verificar_conexion(conexion, usuario_esperado: str) -> None:
    base, cuenta, usuario, puerto = conexion.execute(text(
        "SELECT DATABASE(), CURRENT_USER(), USER(), @@port"
    )).one()
    if (base != "recon_dev" or puerto != 3306
            or not isinstance(cuenta, str) or cuenta.partition("@")[0] != usuario_esperado
            or not isinstance(usuario, str) or usuario.partition("@")[0] != usuario_esperado):
        raise VerificacionFallida("La identidad real de la conexión administrativa no coincide.")

    grants = [fila[0] for fila in conexion.execute(text("SHOW GRANTS FOR CURRENT_USER()"))]
    if not all(isinstance(fila, str) for fila in grants) or not privilegios_suficientes(grants):
        raise VerificacionFallida(
            "La cuenta administrativa no acredita visibilidad completa de eventos, "
            "rutinas y triggers."
        )

    eventos = conexion.scalar(text(
        "SELECT COUNT(*) FROM information_schema.EVENTS WHERE EVENT_SCHEMA = 'recon_dev'"
    ))
    rutinas = conexion.scalar(text(
        "SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA = 'recon_dev'"
    ))
    triggers = conexion.scalar(text(
        "SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = 'recon_dev'"
    ))
    conteos = (eventos, rutinas, triggers)
    if any(type(conteo) is not int or conteo < 0 for conteo in conteos):
        raise VerificacionFallida("Los conteos de objetos almacenados no son concluyentes.")
    if any(conteo != 0 for conteo in conteos):
        raise VerificacionFallida(
            "Hay eventos, rutinas o triggers en recon_dev; el respaldo de tablas sería incompleto."
        )


def verificar() -> None:
    usuario = os.getenv("RECON_BACKUP_ADMIN_USER", "")
    clave = os.getenv("RECON_BACKUP_ADMIN_PASSWORD", "")
    if not usuario or usuario in {"recon_dev_app", "recon_test_app"} or not clave:
        raise VerificacionFallida("Se exige una cuenta administrativa distinta de la aplicación.")
    url = URL.create(
        "mysql+pymysql", username=usuario, password=clave,
        host="127.0.0.1", port=3306, database="recon_dev",
        query={"charset": "utf8mb4"},
    )
    motor = create_engine(url, poolclass=NullPool)
    try:
        with motor.connect() as conexion:
            verificar_conexion(conexion, usuario)
    finally:
        motor.dispose()


def main() -> int:
    if len(sys.argv) != 1:
        print("NO APTO: el verificador administrativo no acepta argumentos.", file=sys.stderr)
        return 1
    try:
        verificar()
    except VerificacionFallida as error:
        print(f"NO APTO: {error}", file=sys.stderr)
        return 1
    except Exception:
        print("NO APTO: falló la comprobación administrativa de solo lectura.", file=sys.stderr)
        return 1
    print("APTO: visibilidad administrativa suficiente y cero eventos, rutinas y triggers en recon_dev.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
