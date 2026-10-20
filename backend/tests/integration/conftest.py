"""Barrera de seguridad y aislamiento transaccional para MySQL real."""

import os
from collections.abc import Iterator

import pytest
from flask import Flask
from sqlalchemy import text
from sqlalchemy.engine import Connection, URL
from sqlalchemy.orm import Session

from recon_platform import create_app
from recon_platform.extensions import db


def _detener(motivo: str) -> None:
    pytest.exit(motivo, returncode=2)


def _validar_url(url: URL) -> None:
    if (
        url.drivername != "mysql+pymysql"
        or url.host != "127.0.0.1"
        or url.port != 3306
        or url.database != "recon_tests"
        or url.username != "recon_test_app"
    ):
        _detener("Destino MySQL de integración no autorizado.")


def _validar_conexion(conexion: Connection) -> None:
    """Comprueba identidad y migración mediante consultas de solo lectura."""
    lectura = None
    try:
        identidad = conexion.execute(
            text("SELECT DATABASE(), CURRENT_USER(), USER(), @@port")
        ).one()
        versiones = conexion.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalars().all()
        motores = dict(
            conexion.execute(
                text(
                    "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN "
                    "('alembic_version', 'tipo_persona', 'persona', "
                    "'rol', 'usuario_plataforma', 'auditoria_iam', 'sesion_usuario', "
                    "'auditoria_personas')"
                )
            ).all()
        )
        lectura = identidad, versiones, motores
    except Exception:
        pass  # El error del controlador podría contener datos de conexión.
    if lectura is None:
        _detener("No se pudo verificar el destino y el esquema MySQL de pruebas.")

    identidad, versiones, motores = lectura
    base, cuenta, usuario_conexion, puerto = identidad
    if (
        base != "recon_tests"
        or cuenta.partition("@")[0] != "recon_test_app"
        or usuario_conexion.partition("@")[0] != "recon_test_app"
        or puerto != 3306
    ):
        _detener("La conexión real no corresponde a MySQL de pruebas autorizado.")
    if versiones not in (["0001_personas"], ["0002_identity_iam"],
                         ["0003_sesiones_iam"], ["0004_auditoria_personas"]):
        _detener("La base de pruebas no tiene una revisión Alembic conocida.")
    esperados = {
        "alembic_version": "InnoDB",
        "tipo_persona": "InnoDB",
        "persona": "InnoDB",
    }
    if versiones in (["0002_identity_iam"], ["0003_sesiones_iam"],
                    ["0004_auditoria_personas"]):
        esperados.update({
            "rol": "InnoDB",
            "usuario_plataforma": "InnoDB",
            "auditoria_iam": "InnoDB",
        })
    if versiones in (["0003_sesiones_iam"], ["0004_auditoria_personas"]):
        esperados["sesion_usuario"] = "InnoDB"
    if versiones == ["0004_auditoria_personas"]:
        esperados["auditoria_personas"] = "InnoDB"
    if motores != esperados:
        _detener("El esquema de pruebas requiere tablas InnoDB para el rollback.")


@pytest.fixture(scope="session")
def aplicacion_mysql() -> Iterator[Flask]:
    if os.getenv("RECON_RUN_MYSQL_INTEGRATION") != "1":
        pytest.skip("Integración MySQL desactivada: falta activación explícita.")
    aplicacion = None
    try:
        aplicacion = create_app(pruebas=True)
    except Exception:
        pass
    if aplicacion is None:
        _detener("Configuración MySQL de pruebas incompleta o inválida.")
    with aplicacion.app_context():
        _validar_url(db.engine.url)
        yield aplicacion


@pytest.fixture
def conexion_mysql(aplicacion_mysql: Flask) -> Iterator[Connection]:
    """Verifica cada conexión física antes de entregarla a una prueba."""
    conexion = None
    try:
        conexion = db.engine.connect()
    except Exception:
        pass
    if conexion is None:
        _detener("No se pudo abrir la conexión MySQL de pruebas.")
    try:
        _validar_conexion(conexion)
        conexion.rollback()  # Cierra la transacción implícita de las consultas.
        yield conexion
    finally:
        conexion.close()


@pytest.fixture
def conexion_iam_mysql(conexion_mysql: Connection) -> Iterator[Connection]:
    """Exige una revisión IAM conocida antes de entregar la conexión."""
    revision = None
    try:
        revision = conexion_mysql.scalar(text("SELECT version_num FROM alembic_version"))
    except Exception:
        pass
    if revision not in {"0002_identity_iam", "0003_sesiones_iam", "0004_auditoria_personas"}:
        _detener("Las pruebas IAM requieren una revisión IAM conocida.")
    conexion_mysql.rollback()
    yield conexion_mysql


@pytest.fixture
def sesion_mysql(conexion_mysql: Connection) -> Iterator[Session]:
    """Los commits del caso de uso quedan dentro de una transacción revertible."""
    transaccion = conexion_mysql.begin()
    sesion = Session(bind=conexion_mysql, join_transaction_mode="create_savepoint")
    try:
        yield sesion
    finally:
        try:
            sesion.close()
        finally:
            if transaccion.is_active:
                transaccion.rollback()


@pytest.fixture
def sesion_iam_mysql(conexion_iam_mysql: Connection) -> Iterator[Session]:
    """Aísla cada prueba IAM con una transacción externa reversible."""
    transaccion = conexion_iam_mysql.begin()
    sesion = Session(bind=conexion_iam_mysql, join_transaction_mode="create_savepoint")
    try:
        yield sesion
    finally:
        try:
            sesion.close()
        finally:
            if transaccion.is_active:
                transaccion.rollback()


@pytest.fixture
def conexion_sesiones_mysql(conexion_iam_mysql: Connection) -> Iterator[Connection]:
    """Exige 0003 antes de permitir escrituras de pruebas de sesiones."""
    revision = conexion_iam_mysql.scalar(text("SELECT version_num FROM alembic_version"))
    if revision not in {"0003_sesiones_iam", "0004_auditoria_personas"}:
        _detener("Las pruebas de sesiones requieren 0003 o una revisión posterior conocida.")
    conexion_iam_mysql.rollback()
    yield conexion_iam_mysql


@pytest.fixture
def sesion_sesiones_mysql(conexion_sesiones_mysql: Connection) -> Iterator[Session]:
    transaccion = conexion_sesiones_mysql.begin()
    sesion = Session(bind=conexion_sesiones_mysql, join_transaction_mode="create_savepoint")
    try:
        yield sesion
    finally:
        try:
            sesion.close()
        finally:
            if transaccion.is_active:
                transaccion.rollback()
