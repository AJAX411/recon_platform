"""Comprobación manual y exclusivamente de lectura previa a 0002_identity_iam."""

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from recon_platform.config import obtener_uri_mysql

DESTINO = ("127.0.0.1", 3306, "recon_tests", "recon_test_app")
VARIABLES = (
    "DB_HOST", "DB_PORT", "DB_NAME", "DB_TEST_NAME",
    "DB_TEST_USER", "DB_TEST_PASSWORD",
)
TABLAS_PERSONAS = {"alembic_version", "tipo_persona", "persona"}
TABLAS_IAM = {"rol", "usuario_plataforma", "auditoria_iam"}


class VerificacionFallida(Exception):
    """Discrepancia que impide considerar segura la migración 0002."""


def verificar() -> None:
    ausentes = [nombre for nombre in VARIABLES if not os.getenv(nombre)]
    if ausentes:
        raise VerificacionFallida(
            "Faltan variables de entorno: " + ", ".join(ausentes) + "."
        )

    # La configuración de pruebas exige credenciales propias y DB_NAME distinto.
    uri = obtener_uri_mysql(pruebas=True)
    if uri is None:
        raise VerificacionFallida("La configuración MySQL de pruebas está incompleta.")
    url = make_url(uri)
    if (
        url.drivername != "mysql+pymysql"
        or (url.host, url.port, url.database, url.username) != DESTINO
    ):
        raise VerificacionFallida(
            "Destino configurado no autorizado: se exige "
            "127.0.0.1:3306/recon_tests con recon_test_app."
        )

    motor = create_engine(url, poolclass=NullPool)
    try:
        with motor.connect() as conexion:
            base, cuenta, usuario, puerto = conexion.execute(
                text("SELECT DATABASE(), CURRENT_USER(), USER(), @@port")
            ).one()
            if (
                base != "recon_tests"
                or cuenta.partition("@")[0] != "recon_test_app"
                or usuario.partition("@")[0] != "recon_test_app"
                or puerto != 3306
            ):
                raise VerificacionFallida(
                    "La identidad real de la conexión no corresponde a recon_tests."
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
                    raise VerificacionFallida(
                        "No se pudo validar el esquema MySQL de pruebas."
                    )
                tablas[nombre] = motor_tabla
            if not TABLAS_PERSONAS.issubset(tablas):
                raise VerificacionFallida("Faltan tablas del esquema de Personas.")
            if TABLAS_IAM.intersection(tablas):
                raise VerificacionFallida(
                    "Existen tablas IAM; puede haber una migración parcial o aplicada."
                )
            if any(tablas[nombre] != "InnoDB" for nombre in TABLAS_PERSONAS):
                raise VerificacionFallida(
                    "Las tablas de Personas o Alembic no utilizan InnoDB."
                )

            revisiones = conexion.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalars().all()
            if revisiones != ["0001_personas"]:
                raise VerificacionFallida(
                    "La revisión Alembic actual no es exactamente 0001_personas."
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
        # Una excepción del controlador podría incluir datos de conexión.
        print(
            "NO APTO: no se pudo completar la comprobación autenticada de MySQL.",
            file=sys.stderr,
        )
        return 1

    print("APTO: destino y cuenta MySQL de pruebas verificados.")
    print("APTO: revisión Alembic 0001_personas.")
    print("APTO: tablas de Personas presentes en InnoDB; tablas IAM ausentes.")
    print("Comprobación de solo lectura completada. No se aplicó ninguna migración.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
