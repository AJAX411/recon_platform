"""Comprobación read-only de 0005 en recon_dev y preservación de datos previos."""

import argparse
import hashlib
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from recon_platform.config import obtener_uri_mysql
from verificar_recon_dev_0002 import VARIABLES, verificar_esquema
from verificar_recon_dev_0003 import verificar_sesion_nueva
from verificar_recon_dev_0004 import (
    TABLAS_PREVIAS, comparar_estado, guardar_estado, huellas_datos,
    validar_destino, validar_identidad,
)
from verificar_recon_tests_0004 import validar_0004
from verificar_recon_tests_0005 import NUEVAS, REVISION, validar_0005, validar_privilegios_migracion


def _exigir(condicion: bool, motivo: str) -> None:
    if not condicion:
        raise ValueError(motivo)


def _huellas(conexion) -> dict:
    estado = huellas_datos(conexion)
    resumen = hashlib.sha256()
    cantidad = 0
    for fila in conexion.execute(text("SELECT * FROM auditoria_personas ORDER BY id_auditoria")):
        contenido = repr(tuple(fila)).encode("utf-8")
        resumen.update(len(contenido).to_bytes(8, "big"))
        resumen.update(contenido)
        cantidad += 1
    estado["auditoria_personas"] = {"filas": cantidad, "huella": resumen.hexdigest()}
    return estado


def verificar(etapa: str, *, guardar: Path | None = None, comparar: Path | None = None) -> None:
    _exigir(etapa in {"antes", "despues"} and not (guardar and comparar), "Etapa o estado inválido.")
    _exigir(etapa != "despues" or comparar is not None,
            "La verificación posterior exige comparar el estado previo.")
    _exigir(all(os.getenv(n) for n in VARIABLES), "Falta configuración de recon_dev.")
    uri = obtener_uri_mysql(pruebas=False)
    if uri is None:
        raise ValueError("Falta URI de recon_dev.")
    url = make_url(uri)
    validar_destino(url)
    motor = create_engine(url, poolclass=NullPool)
    try:
        with motor.connect() as conexion:
            validar_identidad(conexion)
            tablas = {clave: valor for clave, valor in conexion.execute(text(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()"
            )).all()}
            esperadas = TABLAS_PREVIAS | {"auditoria_personas"} | (NUEVAS if etapa == "despues" else set())
            _exigir(set(tablas) == esperadas and all(m == "InnoDB" for m in tablas.values()),
                    "Tablas o motores inesperados.")
            revisiones = conexion.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
            _exigir(revisiones == [REVISION if etapa == "despues" else "0004_auditoria_personas"],
                    "Revisión Alembic inesperada.")
            if etapa == "antes":
                validar_privilegios_migracion(conexion, "recon_dev")
            verificar_esquema(conexion)
            _exigir(set(conexion.execute(text("SELECT nombre FROM rol")).scalars())
                    == {"SUPERADMIN", "ADMINISTRADOR", "OPERADOR"},
                    "Catálogo de roles inesperado.")
            _exigir(conexion.scalar(text(
                "SELECT COUNT(*) FROM usuario_plataforma u JOIN rol r ON r.id_rol=u.id_rol "
                "WHERE r.nombre='SUPERADMIN'"
            )) == 1, "Se exige una sola cuenta SUPERADMIN.")
            _exigir(conexion.scalar(text(
                "SELECT COUNT(*) FROM usuario_plataforma u JOIN rol r ON r.id_rol=u.id_rol "
                "WHERE r.nombre='SUPERADMIN' AND u.estado='ACTIVO'"
            )) == 1, "Se exige un único SUPERADMIN operativo.")
            verificar_sesion_nueva(conexion, exigir_vacia=False)
            validar_0004(conexion)
            if etapa == "despues":
                validar_0005(conexion)
                _exigir(all(conexion.scalar(text(f"SELECT COUNT(*) FROM `{tabla}`")) == 0
                            for tabla in NUEVAS), "Las tablas 0005 deben estar vacías tras migrar.")
            estado = _huellas(conexion)
    finally:
        motor.dispose()
    if guardar is not None:
        guardar_estado(guardar, estado)
    if comparar is not None:
        comparar_estado(comparar, estado)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificación read-only 0005 en recon_dev.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--antes", action="store_true")
    grupo.add_argument("--despues", action="store_true")
    estado = parser.add_mutually_exclusive_group()
    estado.add_argument("--guardar-estado", type=Path)
    estado.add_argument("--comparar-estado", type=Path)
    args = parser.parse_args()
    try:
        verificar("antes" if args.antes else "despues",
                 guardar=args.guardar_estado, comparar=args.comparar_estado)
    except Exception:
        print("NO APTO: identidad, esquema, revisión o datos previos de recon_dev inesperados.", file=sys.stderr)
        return 1
    print("APTO: recon_dev, revisión, esquema y datos previos verificados; solo lectura.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
