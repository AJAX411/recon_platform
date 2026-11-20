"""Repositorio SQLAlchemy para sesiones de usuarios humanos."""

from datetime import datetime

from flask_sqlalchemy.session import Session as SesionFlask
from sqlalchemy.orm import Session, scoped_session

from recon_platform.identidad.sesion import SesionUsuario
from recon_platform.identidad.modelos import SesionUsuarioModelo


class RepositorioSesionesSQLAlchemy:
    def __init__(self, sesion: Session | scoped_session[SesionFlask]) -> None:
        self.sesion = sesion

    def obtener(self, digest: str) -> SesionUsuario | None:
        modelo = self.sesion.get(SesionUsuarioModelo, digest)
        if modelo is None:
            return None
        return SesionUsuario(
            digest=modelo.digest, id_usuario=modelo.id_usuario,
            fecha_creacion=modelo.fecha_creacion, fecha_actividad=modelo.fecha_actividad,
            fecha_expiracion=modelo.fecha_expiracion, fecha_revocacion=modelo.fecha_revocacion,
        )

    def guardar(self, sesion: SesionUsuario) -> None:
        self.sesion.add(SesionUsuarioModelo(
            digest=sesion.digest, id_usuario=sesion.id_usuario,
            fecha_creacion=sesion.fecha_creacion, fecha_actividad=sesion.fecha_actividad,
            fecha_expiracion=sesion.fecha_expiracion, fecha_revocacion=sesion.fecha_revocacion,
        ))

    def actualizar_actividad(self, digest: str, ahora: datetime) -> None:
        modelo = self.sesion.get(SesionUsuarioModelo, digest)
        if modelo is not None:
            modelo.fecha_actividad = ahora

    def revocar(self, digest: str, ahora: datetime) -> None:
        modelo = self.sesion.get(SesionUsuarioModelo, digest)
        if modelo is not None:
            modelo.fecha_revocacion = ahora
