"""Cuenta web independiente de Persona y de la biometría."""

import re
from dataclasses import dataclass, field
from datetime import datetime

from recon_platform.identidad.dominio.rol import Rol

ESTADOS_CUENTA = frozenset({"ACTIVO", "INACTIVO"})
PATRON_LOGIN = re.compile(r"[a-z0-9][a-z0-9._-]{2,63}\Z")


def normalizar_login(valor: str) -> str:
    if not isinstance(valor, str):
        raise ValueError("El identificador de login no es válido.")
    normalizado = valor.strip().casefold()
    if not PATRON_LOGIN.fullmatch(normalizado):
        raise ValueError("El identificador de login no es válido.")
    return normalizado


@dataclass(kw_only=True, slots=True)
class UsuarioPlataforma:
    login: str
    hash_contrasena: str = field(repr=False)
    rol: Rol
    estado: str = "ACTIVO"
    id_usuario: int | None = None
    fecha_creacion: datetime | None = None
    fecha_actualizacion: datetime | None = None

    def __post_init__(self) -> None:
        self.login = normalizar_login(self.login)
        if (
            not isinstance(self.hash_contrasena, str)
            or not self.hash_contrasena.startswith("scrypt:")
            or self.hash_contrasena.count("$") != 2
            or len(self.hash_contrasena) > 255
        ):
            raise ValueError("La cuenta requiere un hash de contraseña.")
        if not isinstance(self.rol, Rol):
            raise ValueError("La cuenta requiere un Rol válido.")
        if not isinstance(self.estado, str) or self.estado not in ESTADOS_CUENTA:
            raise ValueError("El estado de cuenta no es válido.")
        if self.id_usuario is not None and (
            type(self.id_usuario) is not int or self.id_usuario <= 0
        ):
            raise ValueError("id_usuario debe ser un entero positivo.")
