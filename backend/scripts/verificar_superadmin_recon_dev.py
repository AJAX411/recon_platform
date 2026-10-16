"""Verificación de solo lectura del primer SUPERADMIN en recon_dev."""

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from recon_platform.config import obtener_uri_mysql
from verificar_recon_dev_0002 import (
    DESTINO,
    ROLES,
    TABLAS,
    VARIABLES,
    VerificacionFallida,
    verificar_esquema,
)


def verificar() -> None:
    ausentes = [nombre for nombre in VARIABLES if not os.getenv(nombre)]
    if ausentes:
        raise VerificacionFallida(
            "Faltan variables de entorno: " + ", ".join(ausentes) + "."
        )

    uri = obtener_uri_mysql(pruebas=False)
    if uri is None:
        raise VerificacionFallida("La configuración MySQL de desarrollo está incompleta.")
    url = make_url(uri)
    if (
        url.drivername != "mysql+pymysql"
        or (url.host, url.port, url.database, url.username) != DESTINO
    ):
        raise VerificacionFallida(
            "Destino configurado no autorizado: se exige "
            "127.0.0.1:3306/recon_dev con recon_dev_app."
        )

    motor = create_engine(url, poolclass=NullPool)
    try:
        with motor.connect() as conexion:
            base, cuenta, usuario, puerto = conexion.execute(
                text("SELECT DATABASE(), CURRENT_USER(), USER(), @@port")
            ).one()
            if (
                base != "recon_dev"
                or cuenta.partition("@")[0] != "recon_dev_app"
                or usuario.partition("@")[0] != "recon_dev_app"
                or puerto != 3306
            ):
                raise VerificacionFallida(
                    "La identidad real de la conexión no corresponde a recon_dev."
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
                    raise VerificacionFallida("No se pudo validar el esquema MySQL.")
                tablas[nombre] = motor_tabla
            if not TABLAS.issubset(tablas):
                raise VerificacionFallida("Faltan tablas de Personas o Identity/IAM.")
            if any(tablas[nombre] != "InnoDB" for nombre in TABLAS):
                raise VerificacionFallida("Alguna tabla requerida no utiliza InnoDB.")

            revisiones = conexion.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalars().all()
            if revisiones != ["0002_identity_iam"]:
                raise VerificacionFallida(
                    "La revisión Alembic actual no es exactamente 0002_identity_iam."
                )
            verificar_esquema(conexion)

            roles = conexion.execute(text("SELECT nombre FROM rol")).scalars().all()
            if len(roles) != 3 or set(roles) != ROLES:
                raise VerificacionFallida("El catálogo de roles es inesperado.")

            total_cuentas = conexion.execute(text(
                "SELECT COUNT(*) FROM usuario_plataforma"
            )).scalar_one()
            if total_cuentas != 1:
                raise VerificacionFallida(
                    "No existe exactamente una cuenta de plataforma."
                )
            cuenta = conexion.execute(text(
                "SELECT u.id_usuario, u.estado, r.nombre AS rol_nombre, "
                "u.hash_contrasena LIKE 'scrypt:%' AS hash_scrypt "
                "FROM usuario_plataforma AS u "
                "JOIN rol AS r ON r.id_rol = u.id_rol"
            )).mappings().one_or_none()
            if (
                cuenta is None or cuenta["estado"] != "ACTIVO"
                or cuenta["rol_nombre"] != "SUPERADMIN"
                or cuenta["hash_scrypt"] != 1
            ):
                raise VerificacionFallida(
                    "La cuenta inicial no es un SUPERADMIN activo con hash scrypt."
                )

            auditorias = conexion.execute(text(
                "SELECT actor_id, usuario_id, accion, resultado, anterior, nuevo "
                "FROM auditoria_iam"
            )).mappings().all()
            if len(auditorias) != 1:
                raise VerificacionFallida("La auditoría inicial es inesperada.")
            auditoria = auditorias[0]
            if (
                auditoria["actor_id"] is not None
                or auditoria["usuario_id"] != cuenta["id_usuario"]
                or auditoria["accion"] != "BOOTSTRAP_SUPERADMIN"
                or auditoria["resultado"] != "EXITO"
                or auditoria["anterior"] is not None
                or auditoria["nuevo"] is not None
            ):
                raise VerificacionFallida("La auditoría inicial es inesperada.")

            persona_presente = conexion.execute(text(
                "SELECT 1 FROM persona WHERE id_persona = 1 LIMIT 1"
            )).scalar_one_or_none()
            if persona_presente != 1:
                raise VerificacionFallida(
                    "No se encontró la Persona de desarrollo con id_persona=1."
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
        # El controlador podría incluir datos de conexión en sus excepciones.
        print(
            "NO APTO: no se pudo completar la comprobación autenticada de MySQL.",
            file=sys.stderr,
        )
        return 1

    print("APTO: destino y cuenta MySQL de desarrollo verificados.")
    print("APTO: revisión Alembic 0002_identity_iam y esquema requeridos.")
    print("APTO: exactamente una cuenta SUPERADMIN activa con hash scrypt.")
    print("APTO: una auditoría de bootstrap vinculada a esa cuenta.")
    print("APTO: Persona con id_persona=1 conservada.")
    print("Comprobación de solo lectura completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
