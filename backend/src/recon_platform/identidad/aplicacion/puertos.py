"""Contratos requeridos por los casos de uso de IAM."""

from typing import Protocol

from recon_platform.identidad.dominio.rol import Rol
from recon_platform.identidad.dominio.usuario_plataforma import UsuarioPlataforma


class RepositorioIAM(Protocol):
    def obtener_rol(self, nombre: str, *, bloquear: bool = False) -> Rol | None: ...

    def obtener_superadmin(self) -> UsuarioPlataforma | None: ...

    def hay_usuarios(self) -> bool: ...

    def obtener_por_id(self, id_usuario: int) -> UsuarioPlataforma | None: ...

    def obtener_por_login(self, login: str) -> UsuarioPlataforma | None: ...

    def agregar(self, usuario: UsuarioPlataforma) -> UsuarioPlataforma: ...

    def actualizar(self, usuario: UsuarioPlataforma) -> UsuarioPlataforma: ...

    def auditar(
        self,
        *,
        accion: str,
        actor_id: int | None,
        usuario_id: int,
        anterior: str | None = None,
        nuevo: str | None = None,
    ) -> None: ...


class UnidadTrabajoIAM(Protocol):
    def confirmar(self) -> None: ...

    def revertir(self) -> None: ...
