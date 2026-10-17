"""Repositorios IAM: flush sin commits y traducción de integridad."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from recon_platform.identidad.aplicacion.casos_de_uso import (
    ConflictoIntegridadIAM,
    UsuarioDuplicado,
    UsuarioNoExiste,
)
from recon_platform.identidad.dominio.rol import Rol
from recon_platform.identidad.dominio.usuario_plataforma import UsuarioPlataforma
from recon_platform.identidad.infraestructura.modelos import (
    AuditoriaIAMModelo,
    RolModelo,
    SesionUsuarioModelo,
    UsuarioPlataformaModelo,
)


def _utc_con_zona(valor: datetime) -> datetime:
    return valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


def _traducir_integridad(error: IntegrityError) -> ValueError:
    argumentos = getattr(error.orig, "args", ())
    codigo = argumentos[0] if argumentos else None
    if codigo == 1062 or "UNIQUE constraint failed" in str(error.orig):
        return UsuarioDuplicado("El identificador de login ya existe.")
    return ConflictoIntegridadIAM("La base de datos rechazó la operación IAM.")


class RepositorioIAMSQLAlchemy:
    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def obtener_rol(self, nombre: str, *, bloquear: bool = False) -> Rol | None:
        consulta = select(RolModelo).where(RolModelo.nombre == nombre)
        if bloquear:
            consulta = consulta.with_for_update()
        modelo = self.sesion.scalar(consulta)
        return None if modelo is None else Rol(nombre=modelo.nombre, id_rol=modelo.id_rol)

    def obtener_superadmin(self) -> UsuarioPlataforma | None:
        modelos = self.sesion.scalars(
            select(UsuarioPlataformaModelo)
            .join(RolModelo, UsuarioPlataformaModelo.id_rol == RolModelo.id_rol)
            .where(RolModelo.nombre == "SUPERADMIN")
            .order_by(UsuarioPlataformaModelo.id_usuario)
            .limit(2)
        ).all()
        if len(modelos) > 1:
            raise ConflictoIntegridadIAM("Existe más de una cuenta SUPERADMIN.")
        return None if not modelos else self._a_dominio(modelos[0])

    def hay_usuarios(self) -> bool:
        return self.sesion.scalar(
            select(UsuarioPlataformaModelo.id_usuario).limit(1)
        ) is not None

    def obtener_por_id(self, id_usuario: int) -> UsuarioPlataforma | None:
        modelo = self.sesion.get(UsuarioPlataformaModelo, id_usuario)
        return None if modelo is None else self._a_dominio(modelo)

    def obtener_por_login(self, login: str) -> UsuarioPlataforma | None:
        modelo = self.sesion.scalar(
            select(UsuarioPlataformaModelo).where(UsuarioPlataformaModelo.login == login)
        )
        return None if modelo is None else self._a_dominio(modelo)

    def agregar(self, usuario: UsuarioPlataforma) -> UsuarioPlataforma:
        if usuario.rol.id_rol is None:
            raise ConflictoIntegridadIAM("El Rol debe existir antes de crear cuentas.")
        modelo = UsuarioPlataformaModelo(
            login=usuario.login,
            hash_contrasena=usuario.hash_contrasena,
            id_rol=usuario.rol.id_rol,
            estado=usuario.estado,
        )
        self.sesion.add(modelo)
        try:
            self.sesion.flush()
        except IntegrityError as error:
            raise _traducir_integridad(error) from error
        return self._a_dominio(modelo)

    def actualizar(self, usuario: UsuarioPlataforma) -> UsuarioPlataforma:
        if usuario.id_usuario is None or usuario.rol.id_rol is None:
            raise ConflictoIntegridadIAM("La cuenta y su Rol deben existir.")
        modelo = self.sesion.get(UsuarioPlataformaModelo, usuario.id_usuario)
        if modelo is None:
            raise UsuarioNoExiste("La cuenta no existe.")
        modelo.login = usuario.login
        modelo.hash_contrasena = usuario.hash_contrasena
        modelo.id_rol = usuario.rol.id_rol
        modelo.estado = usuario.estado
        try:
            self.sesion.flush()
        except IntegrityError as error:
            raise _traducir_integridad(error) from error
        self.sesion.expire(modelo, ["rol"])
        return self._a_dominio(modelo)

    def revocar_sesiones(self, id_usuario: int) -> None:
        self.sesion.execute(
            update(SesionUsuarioModelo)
            .where(
                SesionUsuarioModelo.id_usuario == id_usuario,
                SesionUsuarioModelo.fecha_revocacion.is_(None),
            )
            .values(fecha_revocacion=datetime.now(UTC).replace(tzinfo=None))
        )

    def auditar(
        self,
        *,
        accion: str,
        actor_id: int | None,
        usuario_id: int,
        anterior: str | None = None,
        nuevo: str | None = None,
    ) -> None:
        self.sesion.add(AuditoriaIAMModelo(
            accion=accion,
            resultado="EXITO",
            actor_id=actor_id,
            usuario_id=usuario_id,
            anterior=anterior,
            nuevo=nuevo,
        ))

    @staticmethod
    def _a_dominio(modelo: UsuarioPlataformaModelo) -> UsuarioPlataforma:
        return UsuarioPlataforma(
            id_usuario=modelo.id_usuario,
            login=modelo.login,
            hash_contrasena=modelo.hash_contrasena,
            rol=Rol(nombre=modelo.rol.nombre, id_rol=modelo.rol.id_rol),
            estado=modelo.estado,
            fecha_creacion=_utc_con_zona(modelo.fecha_creacion),
            fecha_actualizacion=_utc_con_zona(modelo.fecha_actualizacion),
        )
