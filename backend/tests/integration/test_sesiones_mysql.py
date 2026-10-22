"""Persistencia real de sesiones: ejecución explícita tras aplicar 0003 en recon_tests."""

import hashlib
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from recon_platform.identidad.aplicacion.casos_de_uso import (
    BootstrapSuperadmin,
    CambiarEstadoUsuario,
    CrearUsuarioPlataforma,
)
from recon_platform.identidad.aplicacion.sesiones import GestionSesiones
from recon_platform.identidad.infraestructura.modelos import SesionUsuarioModelo, UsuarioPlataformaModelo
from recon_platform.identidad.infraestructura.repositorios import RepositorioIAMSQLAlchemy
from recon_platform.identidad.infraestructura.sesiones import RepositorioSesionesSQLAlchemy
from recon_platform.identidad.infraestructura.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy

pytestmark = pytest.mark.mysql_integration
AHORA = datetime(2026, 10, 16, 12, 0)
CLAVE = "Clave-Ficticia-Sesion-2026!"


def _gestor(sesion: Session) -> GestionSesiones:
    return GestionSesiones(
        RepositorioSesionesSQLAlchemy(sesion), RepositorioIAMSQLAlchemy(sesion),
        UnidadTrabajoIAMSQLAlchemy(sesion), "clave-ficticia-integracion-de-32-caracteres",
    )


def test_esquema_sesiones_y_revision(conexion_sesiones_mysql: Connection) -> None:
    assert conexion_sesiones_mysql.scalar(text("SELECT version_num FROM alembic_version")) in {
        "0003_sesiones_iam", "0004_auditoria_personas", "0005_puntos_edge_auditoria",
        "0006_evento_acceso"
    }
    inspector = inspect(conexion_sesiones_mysql)
    columnas = {col["name"]: col for col in inspector.get_columns("sesion_usuario")}
    assert set(columnas) == {
        "digest", "id_usuario", "fecha_creacion", "fecha_actividad",
        "fecha_expiracion", "fecha_revocacion",
    }
    assert {nombre for nombre, col in columnas.items() if col["nullable"]} == {
        "id_usuario", "fecha_revocacion"
    }
    assert inspector.get_pk_constraint("sesion_usuario")["constrained_columns"] == ["digest"]
    assert {
        fk["name"]: (fk["constrained_columns"], fk["referred_table"])
        for fk in inspector.get_foreign_keys("sesion_usuario")
    } == {"fk_sesion_usuario_cuenta": (["id_usuario"], "usuario_plataforma")}
    assert any(
        indice["name"] == "ix_sesion_usuario_id_usuario"
        for indice in inspector.get_indexes("sesion_usuario")
    )


def test_sesiones_independientes_revocables_y_sin_token_claro(
    sesion_sesiones_mysql: Session,
) -> None:
    repo_iam = RepositorioIAMSQLAlchemy(sesion_sesiones_mysql)
    admin = BootstrapSuperadmin(
        repo_iam, UnidadTrabajoIAMSQLAlchemy(sesion_sesiones_mysql)
    ).ejecutar(login=f"sesion.{uuid4().hex[:20]}", contrasena=CLAVE).usuario
    gestor = _gestor(sesion_sesiones_mysql)
    anonima = gestor.iniciar_anonima(AHORA)
    autenticada = gestor.iniciar_autenticada(anonima, admin.login, CLAVE, AHORA)
    assert autenticada is not None
    primera, identidad = autenticada
    assert identidad.id_usuario == admin.id_usuario
    segunda = gestor.iniciar_anonima(AHORA)
    otra = gestor.iniciar_autenticada(segunda, admin.login, CLAVE, AHORA)
    assert otra is not None and otra[0] != primera
    digest_primera = hashlib.sha256(primera.encode("ascii")).hexdigest()
    digest_otra = hashlib.sha256(otra[0].encode("ascii")).hexdigest()
    guardadas = sesion_sesiones_mysql.scalars(
        select(SesionUsuarioModelo).where(SesionUsuarioModelo.id_usuario == admin.id_usuario)
    ).all()
    assert {sesion.digest for sesion in guardadas} == {digest_primera, digest_otra}
    assert primera not in {sesion.digest for sesion in guardadas}
    assert otra[0] not in {sesion.digest for sesion in guardadas}
    assert gestor.cerrar(primera, AHORA + timedelta(minutes=1))
    assert gestor.identidad_actual(primera, AHORA + timedelta(minutes=2)) is None
    assert gestor.identidad_actual(otra[0], AHORA + timedelta(minutes=2)) is not None
    assert sesion_sesiones_mysql.scalar(
        select(func.count()).select_from(SesionUsuarioModelo).where(
            SesionUsuarioModelo.id_usuario == admin.id_usuario
        )
    ) == 2
    assert sesion_sesiones_mysql.scalar(
        select(func.count()).select_from(SesionUsuarioModelo).where(
            SesionUsuarioModelo.digest == primera
        )
    ) == 0


def test_mysql_rechaza_fk_de_cuenta_inexistente_y_revierte(
    sesion_sesiones_mysql: Session,
) -> None:
    maximo = sesion_sesiones_mysql.scalar(select(func.max(UsuarioPlataformaModelo.id_usuario)))
    inexistente = (maximo or 0) + 100000
    digest = uuid4().hex + uuid4().hex
    sesion_sesiones_mysql.add(SesionUsuarioModelo(
        digest=digest, id_usuario=inexistente,
        fecha_creacion=AHORA, fecha_actividad=AHORA,
        fecha_expiracion=AHORA + timedelta(hours=8),
    ))
    with pytest.raises(IntegrityError):
        sesion_sesiones_mysql.flush()
    sesion_sesiones_mysql.rollback()
    assert sesion_sesiones_mysql.get(SesionUsuarioModelo, digest) is None


def test_desactivacion_revoca_sesiones_en_la_transaccion_iam(
    sesion_sesiones_mysql: Session,
) -> None:
    repo = RepositorioIAMSQLAlchemy(sesion_sesiones_mysql)
    unidad = UnidadTrabajoIAMSQLAlchemy(sesion_sesiones_mysql)
    admin = BootstrapSuperadmin(repo, unidad).ejecutar(
        login=f"sesion.{uuid4().hex[:20]}", contrasena=CLAVE
    ).usuario
    cuenta = CrearUsuarioPlataforma(repo, unidad).ejecutar(
        actor_id=admin.id_usuario, login=f"sesion.{uuid4().hex[:20]}",
        contrasena=CLAVE, rol_nombre="OPERADOR",
    )
    gestor = _gestor(sesion_sesiones_mysql)
    anonima = gestor.iniciar_anonima(AHORA)
    resultado = gestor.iniciar_autenticada(anonima, cuenta.login, CLAVE, AHORA)
    assert resultado is not None
    token, _ = resultado
    CambiarEstadoUsuario(repo, unidad).ejecutar(
        actor_id=admin.id_usuario, usuario_id=cuenta.id_usuario, estado="INACTIVO"
    )
    revocada = sesion_sesiones_mysql.scalar(
        select(SesionUsuarioModelo).where(SesionUsuarioModelo.id_usuario == cuenta.id_usuario)
    )
    assert revocada is not None and revocada.fecha_revocacion is not None
    CambiarEstadoUsuario(repo, unidad).ejecutar(
        actor_id=admin.id_usuario, usuario_id=cuenta.id_usuario, estado="ACTIVO"
    )
    assert gestor.identidad_actual(token, AHORA + timedelta(minutes=1)) is None
