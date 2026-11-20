"""Puertos de aplicación existentes."""

from datetime import datetime
from typing import Protocol

from recon_platform.identidad.sesion import SesionUsuario


class RepositorioSesiones(Protocol):
    def obtener(self, digest: str) -> SesionUsuario | None: ...

    def guardar(self, sesion: SesionUsuario) -> None: ...

    def actualizar_actividad(self, digest: str, ahora: datetime) -> None: ...

    def revocar(self, digest: str, ahora: datetime) -> None: ...
