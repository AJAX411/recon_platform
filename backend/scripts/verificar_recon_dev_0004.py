"""Verifica por lectura recon_dev antes/después de 0004, sin revelar datos.

El estado privado permite comparar todas las filas de las tablas anteriores.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.pool import NullPool

from recon_platform.config import obtener_uri_mysql
from verificar_recon_dev_0002 import (
    DESTINO, TABLAS, VARIABLES, VerificacionFallida, verificar_esquema,
)
from verificar_recon_dev_0003 import (
    exigir, verificar_datos_previos, verificar_sesion_nueva,
)
from verificar_recon_tests_0004 import (
    VerificacionFallida as Check0004Fallido, validar_0004,
)

REVISIONES = {"antes": "0003_sesiones_iam", "despues": "0004_auditoria_personas"}
TABLAS_PREVIAS = TABLAS | {"sesion_usuario"}
CLAVES_DATOS = {
    "tipo_persona": "id_tipo_persona",
    "persona": "id_persona",
    "rol": "id_rol",
    "usuario_plataforma": "id_usuario",
    "auditoria_iam": "id_auditoria",
    "sesion_usuario": "digest",
}


def validar_destino(url) -> None:
    exigir(url.drivername == "mysql+pymysql"
           and (url.host, url.port, url.database, url.username) == DESTINO,
           "El destino debe ser recon_dev/recon_dev_app local.")


def validar_identidad(conexion: Connection) -> None:
    base, cuenta, usuario, puerto = conexion.execute(text(
        "SELECT DATABASE(), CURRENT_USER(), USER(), @@port"
    )).one()
    exigir(base == "recon_dev" and puerto == 3306
           and isinstance(cuenta, str) and cuenta.partition("@")[0] == "recon_dev_app"
           and isinstance(usuario, str) and usuario.partition("@")[0] == "recon_dev_app",
           "La identidad real de MySQL no corresponde a recon_dev.")


def validar_tablas_y_revision(conexion: Connection, etapa: str) -> None:
    tablas = {clave: valor for clave, valor in conexion.execute(text(
        "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE()"
    )).all()}
    esperadas = TABLAS_PREVIAS | ({"auditoria_personas"} if etapa == "despues" else set())
    exigir(set(tablas) == esperadas and all(motor == "InnoDB" for motor in tablas.values()),
           "Tablas o motores de recon_dev inesperados.")
    revisiones = conexion.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    exigir(revisiones == [REVISIONES[etapa]], "La revisión Alembic no corresponde a la etapa.")


def huellas_datos(conexion: Connection) -> dict[str, dict[str, int | str]]:
    """Resume filas previas sin conservar valores, credenciales ni hashes de cuentas."""
    estado = {}
    for tabla, clave in CLAVES_DATOS.items():
        resumen = hashlib.sha256()
        cantidad = 0
        # Los identificadores proceden exclusivamente del mapa constante anterior.
        for fila in conexion.execute(text(f"SELECT * FROM `{tabla}` ORDER BY `{clave}`")):
            contenido = repr(tuple(fila)).encode("utf-8")
            resumen.update(len(contenido).to_bytes(8, "big"))
            resumen.update(contenido)
            cantidad += 1
        estado[tabla] = {"filas": cantidad, "huella": resumen.hexdigest()}
    return estado


def guardar_estado(ruta: Path, estado: dict) -> None:
    try:
        contenido = json.dumps({"version": 1, "tablas": estado}, sort_keys=True)
        descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            archivo.write(contenido)
    except FileExistsError as error:
        raise VerificacionFallida("El archivo de estado ya existe; no se sobrescribe.") from error
    except (OSError, UnicodeError, TypeError, ValueError) as error:
        raise VerificacionFallida("No se pudo escribir el JSON privado de estado.") from error


def comparar_estado(ruta: Path, estado: dict) -> None:
    try:
        guardado = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise VerificacionFallida("No se pudo leer el estado privado previo.") from error
    exigir(guardado == {"version": 1, "tablas": estado},
           "Los datos previos cambiaron; detener y revisar recon_dev.")


def verificar(etapa: str, *, guardar: Path | None = None,
             comparar: Path | None = None) -> None:
    exigir(etapa in REVISIONES, "Etapa inválida.")
    exigir(not (guardar and comparar), "Guardar y comparar estado son excluyentes.")
    exigir(etapa != "despues" or comparar is not None,
           "La verificación posterior exige el estado previo.")
    exigir(all(os.getenv(nombre) for nombre in VARIABLES),
           "Falta configuración explícita de MySQL de desarrollo.")
    try:
        uri = obtener_uri_mysql(pruebas=False)
        if uri is None:
            raise VerificacionFallida("La configuración MySQL de desarrollo está incompleta.")
        url = make_url(uri)
        validar_destino(url)
    except VerificacionFallida:
        raise
    except Exception as error:
        raise VerificacionFallida("No se pudo preparar la configuración MySQL de desarrollo.") from error
    try:
        motor = create_engine(url, poolclass=NullPool)
    except Exception as error:
        raise VerificacionFallida("No se pudo preparar la conexión MySQL de desarrollo.") from error
    try:
        try:
            with motor.connect() as conexion:
                try:
                    validar_identidad(conexion)
                    validar_tablas_y_revision(conexion, etapa)
                    verificar_esquema(conexion)
                    verificar_datos_previos(conexion)
                    verificar_sesion_nueva(conexion, exigir_vacia=False)
                    borrados = {clave: valor for clave, valor in conexion.execute(text(
                        "SELECT CONSTRAINT_NAME, DELETE_RULE "
                        "FROM information_schema.REFERENTIAL_CONSTRAINTS "
                        "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'sesion_usuario'"
                    )).all()}
                    exigir(borrados == {"fk_sesion_usuario_cuenta": "RESTRICT"},
                           "La política de borrado de sesión no coincide con 0003.")
                    if etapa == "despues":
                        try:
                            validar_0004(conexion)
                        except Check0004Fallido as error:
                            raise VerificacionFallida(str(error)) from error
                        exigir(conexion.scalar(text("SELECT COUNT(*) FROM auditoria_personas")) == 0,
                               "La auditoría de Personas debe estar vacía tras 0004.")
                    estado = huellas_datos(conexion)
                except VerificacionFallida as error:
                    raise VerificacionFallida(f"Validación de esquema/datos: {error}") from error
                except Exception as error:
                    raise VerificacionFallida(
                        "No se pudo completar la validación de esquema/datos de recon_dev."
                    ) from error
        except VerificacionFallida:
            raise
        except Exception as error:
            raise VerificacionFallida("No se pudo establecer la conexión MySQL de desarrollo.") from error
    finally:
        motor.dispose()
    if guardar is not None:
        guardar_estado(guardar, estado)
    if comparar is not None:
        comparar_estado(comparar, estado)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificación de lectura de 0004 en recon_dev.")
    etapa = parser.add_mutually_exclusive_group(required=True)
    etapa.add_argument("--antes", action="store_true")
    etapa.add_argument("--despues", action="store_true")
    estado = parser.add_mutually_exclusive_group()
    estado.add_argument("--guardar-estado", type=Path)
    estado.add_argument("--comparar-estado", type=Path)
    argumentos = parser.parse_args()
    try:
        verificar("antes" if argumentos.antes else "despues",
                 guardar=argumentos.guardar_estado, comparar=argumentos.comparar_estado)
    except VerificacionFallida as error:
        print(f"NO APTO: {error}", file=sys.stderr)
        return 1
    except Exception:
        print("NO APTO: error inesperado del verificador de recon_dev.",
              file=sys.stderr)
        return 1
    print("APTO: identidad real, revisión, esquema y datos previos verificados.")
    if argumentos.despues:
        print("APTO: auditoria_personas y sus restricciones verificadas.")
    print("Verificación de base exclusivamente de lectura completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
