"""Adaptador IAM con SQLite efímero; la migración real se valida con MySQL aparte."""

from datetime import UTC
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from recon_platform.extensions import db
from recon_platform.identidad.servicio_cuentas import AutenticarUsuarioPlataforma, BootstrapSuperadmin, CambiarEstadoUsuario, CambiarLoginUsuario, CambiarRolUsuario, ConflictoIntegridadIAM, CrearUsuarioPlataforma, RestablecerContrasenaUsuario
from recon_platform.identidad.usuario_plataforma import UsuarioPlataforma
from recon_platform.identidad.modelos import AuditoriaIAMModelo, RolModelo, UsuarioPlataformaModelo
from recon_platform.identidad.repositorio_cuentas import RepositorioIAMSQLAlchemy
from recon_platform.identidad.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy


def test_repositorio_detecta_cuentas_existentes_y_superadmin_duplicado() -> None:
    motor = create_engine("sqlite+pysqlite:///:memory:")
    try:
        RolModelo.__table__.create(motor)
        UsuarioPlataformaModelo.__table__.create(motor)
        with Session(motor) as sesion:
            sesion.add(RolModelo(nombre="SUPERADMIN"))
            sesion.commit()
            repositorio = RepositorioIAMSQLAlchemy(sesion)
            assert not repositorio.hay_usuarios()
            rol_id = sesion.scalar(select(RolModelo.id_rol))
            sesion.add_all(
                UsuarioPlataformaModelo(
                    login=login,
                    hash_contrasena="scrypt:hash-ficticio$sal$ficticio",
                    id_rol=rol_id,
                )
                for login in ("admin.uno", "admin.dos")
            )
            sesion.commit()
            assert repositorio.hay_usuarios()
            with pytest.raises(ConflictoIntegridadIAM, match="más de una"):
                repositorio.obtener_superadmin()
    finally:
        motor.dispose()


@pytest.fixture
def sesion_iam_unitaria() -> Iterator[Session]:
    motor = create_engine("sqlite+pysqlite:///:memory:")
    try:
        for tabla in ("rol", "usuario_plataforma", "auditoria_iam", "sesion_usuario"):
            db.metadata.tables[tabla].create(motor)
        with Session(motor) as sesion:
            sesion.execute(db.metadata.tables["rol"].insert(), [
                {"nombre": nombre} for nombre in ("SUPERADMIN", "ADMINISTRADOR", "OPERADOR")
            ])
            sesion.commit()
            yield sesion
    finally:
        motor.dispose()


def _inicializar_cuenta(repo: RepositorioIAMSQLAlchemy, unidad: UnidadTrabajoIAMSQLAlchemy) -> int:
    cuenta = BootstrapSuperadmin(repo, unidad).ejecutar(
        login="admin.fase1", contrasena="Clave-Ficticia-Prueba-2026!").usuario
    identificador = cuenta.id_usuario
    assert identificador is not None
    return identificador


@pytest.mark.parametrize("operacion", ["bootstrap", "crear"])
def test_alta_iam_sin_id_devuelto_revierte_cuenta_y_auditoria(
    sesion_iam_unitaria: Session, monkeypatch, operacion: str,
):
    sesion = sesion_iam_unitaria
    repo = RepositorioIAMSQLAlchemy(sesion)
    unidad = UnidadTrabajoIAMSQLAlchemy(sesion)
    actor_id = _inicializar_cuenta(repo, unidad) if operacion == "crear" else None
    cuentas_antes = sesion.scalar(select(func.count()).select_from(UsuarioPlataformaModelo))
    eventos_antes = sesion.scalar(select(func.count()).select_from(AuditoriaIAMModelo))
    original = repo.agregar

    def agregar_sin_id(usuario: UsuarioPlataforma) -> UsuarioPlataforma:
        guardado = original(usuario)
        guardado.id_usuario = None
        return guardado

    def ejecutar():
        if operacion == "bootstrap":
            return BootstrapSuperadmin(repo, unidad).ejecutar(
                login="admin.fase1", contrasena="Clave-Ficticia-Prueba-2026!").usuario
        assert actor_id is not None
        return CrearUsuarioPlataforma(repo, unidad).ejecutar(actor_id=actor_id,
            login="operador.fase1", contrasena="Clave-Ficticia-Prueba-2026!", rol_nombre="OPERADOR")

    monkeypatch.setattr(repo, "agregar", agregar_sin_id)
    with pytest.raises(ConflictoIntegridadIAM, match="ID de cuenta válido"):
        ejecutar()
    assert sesion.scalar(select(func.count()).select_from(UsuarioPlataformaModelo)) == cuentas_antes
    assert sesion.scalar(select(func.count()).select_from(AuditoriaIAMModelo)) == eventos_antes
    monkeypatch.setattr(repo, "agregar", original)
    assert ejecutar().id_usuario is not None


@pytest.mark.parametrize("operacion", ["rol", "estado", "login", "contrasena"])
def test_objetivo_iam_sin_id_no_se_actualiza_ni_se_audita(
    sesion_iam_unitaria: Session, monkeypatch, operacion: str,
):
    sesion = sesion_iam_unitaria
    repo = RepositorioIAMSQLAlchemy(sesion)
    unidad = UnidadTrabajoIAMSQLAlchemy(sesion)
    actor_id = _inicializar_cuenta(repo, unidad)
    cuenta = CrearUsuarioPlataforma(repo, unidad).ejecutar(actor_id=actor_id,
        login="operador.fase1", contrasena="Clave-Ficticia-Prueba-2026!", rol_nombre="OPERADOR")
    id_objetivo = cuenta.id_usuario
    assert id_objetivo is not None
    eventos_antes = sesion.scalar(select(func.count()).select_from(AuditoriaIAMModelo))
    original = repo.obtener_por_id

    def obtener_sin_id(identificador: int) -> UsuarioPlataforma | None:
        usuario = original(identificador)
        if usuario is not None and identificador == id_objetivo:
            usuario.id_usuario = None
        return usuario

    def ejecutar():
        if operacion == "rol":
            return CambiarRolUsuario(repo, unidad).ejecutar(actor_id=actor_id,
                usuario_id=id_objetivo, rol_nombre="ADMINISTRADOR")
        if operacion == "estado":
            return CambiarEstadoUsuario(repo, unidad).ejecutar(actor_id=actor_id,
                usuario_id=id_objetivo, estado="INACTIVO")
        if operacion == "login":
            return CambiarLoginUsuario(repo, unidad).ejecutar(actor_id=actor_id,
                usuario_id=id_objetivo, login="nuevo.fase1")
        return RestablecerContrasenaUsuario(repo, unidad).ejecutar(actor_id=actor_id,
            usuario_id=id_objetivo, nueva_contrasena="Otra-Clave-Ficticia-Prueba-2026!")

    monkeypatch.setattr(repo, "obtener_por_id", obtener_sin_id)
    with pytest.raises(ConflictoIntegridadIAM, match="ID de cuenta válido"):
        ejecutar()
    conservada = original(id_objetivo)
    assert conservada is not None
    assert conservada.login == "operador.fase1"
    assert conservada.estado == "ACTIVO" and conservada.rol.nombre == "OPERADOR"
    assert sesion.scalar(select(func.count()).select_from(AuditoriaIAMModelo)) == eventos_antes
    monkeypatch.setattr(repo, "obtener_por_id", original)
    assert ejecutar().id_usuario == id_objetivo


def test_autenticacion_no_produce_identidad_con_id_ausente(sesion_iam_unitaria: Session, monkeypatch):
    repo = RepositorioIAMSQLAlchemy(sesion_iam_unitaria)
    unidad = UnidadTrabajoIAMSQLAlchemy(sesion_iam_unitaria)
    actor_id = _inicializar_cuenta(repo, unidad)
    original = repo.obtener_por_login

    def obtener_sin_id(login: str) -> UsuarioPlataforma | None:
        usuario = original(login)
        if usuario is not None:
            usuario.id_usuario = None
        return usuario

    monkeypatch.setattr(repo, "obtener_por_login", obtener_sin_id)
    with pytest.raises(ConflictoIntegridadIAM, match="ID de cuenta válido"):
        AutenticarUsuarioPlataforma(repo, unidad).ejecutar(
            login="admin.fase1", contrasena="Clave-Ficticia-Prueba-2026!")
    monkeypatch.setattr(repo, "obtener_por_login", original)
    identidad = AutenticarUsuarioPlataforma(repo, unidad).ejecutar(
        login="admin.fase1", contrasena="Clave-Ficticia-Prueba-2026!")
    assert identidad is not None and identidad.id_usuario == actor_id


def test_repositorio_persiste_cuentas_roles_y_auditoria_en_sesiones_distintas() -> None:
    motor = create_engine("sqlite+pysqlite:///:memory:")
    try:
        RolModelo.__table__.create(motor)
        UsuarioPlataformaModelo.__table__.create(motor)
        AuditoriaIAMModelo.__table__.create(motor)
        with Session(motor) as sesion:
            sesion.add_all(RolModelo(nombre=nombre) for nombre in (
                "SUPERADMIN", "ADMINISTRADOR", "OPERADOR"
            ))
            sesion.commit()
            repositorio = RepositorioIAMSQLAlchemy(sesion)
            unidad = UnidadTrabajoIAMSQLAlchemy(sesion)
            inicial = BootstrapSuperadmin(repositorio, unidad).ejecutar(
                login="admin.ficticio", contrasena="Clave-Ficticia-Prueba-2026!"
            ).usuario
            assert inicial.id_usuario is not None
            cuenta = CrearUsuarioPlataforma(repositorio, unidad).ejecutar(
                actor_id=inicial.id_usuario, login="operador.ficticio",
                contrasena="Otra-Clave-Ficticia-2026!", rol_nombre="OPERADOR",
            )
            assert cuenta.id_usuario is not None
            CambiarRolUsuario(repositorio, unidad).ejecutar(
                actor_id=inicial.id_usuario, usuario_id=cuenta.id_usuario,
                rol_nombre="ADMINISTRADOR",
            )
            id_cuenta = cuenta.id_usuario

        with Session(motor) as sesion:
            guardada = RepositorioIAMSQLAlchemy(sesion).obtener_por_id(id_cuenta)
            assert guardada is not None
            assert guardada.rol.nombre == "ADMINISTRADOR"
            assert guardada.fecha_creacion is not None
            assert guardada.fecha_actualizacion is not None
            assert guardada.fecha_creacion.tzinfo == UTC
            assert guardada.fecha_actualizacion.tzinfo == UTC
            assert sesion.scalar(select(func.count()).select_from(AuditoriaIAMModelo)) == 3
            assert sesion.scalar(select(AuditoriaIAMModelo.nuevo).where(
                AuditoriaIAMModelo.accion == "CAMBIAR_ROL"
            )) == "ADMINISTRADOR"
    finally:
        motor.dispose()
