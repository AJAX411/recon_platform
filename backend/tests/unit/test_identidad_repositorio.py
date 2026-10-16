"""Adaptador IAM con SQLite efímero; la migración real se valida con MySQL aparte."""

from datetime import UTC

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from recon_platform.identidad.aplicacion.casos_de_uso import (
    BootstrapSuperadmin,
    CambiarRolUsuario,
    ConflictoIntegridadIAM,
    CrearUsuarioPlataforma,
)
from recon_platform.identidad.infraestructura.modelos import (
    AuditoriaIAMModelo,
    RolModelo,
    UsuarioPlataformaModelo,
)
from recon_platform.identidad.infraestructura.repositorios import RepositorioIAMSQLAlchemy
from recon_platform.identidad.infraestructura.unidad_trabajo import (
    UnidadTrabajoIAMSQLAlchemy,
)


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
            cuenta = CrearUsuarioPlataforma(repositorio, unidad).ejecutar(
                actor_id=inicial.id_usuario, login="operador.ficticio",
                contrasena="Otra-Clave-Ficticia-2026!", rol_nombre="OPERADOR",
            )
            CambiarRolUsuario(repositorio, unidad).ejecutar(
                actor_id=inicial.id_usuario, usuario_id=cuenta.id_usuario,
                rol_nombre="ADMINISTRADOR",
            )
            id_cuenta = cuenta.id_usuario

        with Session(motor) as sesion:
            guardada = RepositorioIAMSQLAlchemy(sesion).obtener_por_id(id_cuenta)
            assert guardada is not None
            assert guardada.rol.nombre == "ADMINISTRADOR"
            assert guardada.fecha_creacion.tzinfo == UTC
            assert guardada.fecha_actualizacion.tzinfo == UTC
            assert sesion.scalar(select(func.count()).select_from(AuditoriaIAMModelo)) == 3
            assert sesion.scalar(select(AuditoriaIAMModelo.nuevo).where(
                AuditoriaIAMModelo.accion == "CAMBIAR_ROL"
            )) == "ADMINISTRADOR"
    finally:
        motor.dispose()
