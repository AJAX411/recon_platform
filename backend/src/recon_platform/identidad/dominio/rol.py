"""Rol único de una cuenta de plataforma."""

from dataclasses import dataclass

ROLES_INICIALES = frozenset({"SUPERADMIN", "ADMINISTRADOR", "OPERADOR"})


@dataclass(kw_only=True, slots=True)
class Rol:
    nombre: str
    id_rol: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.nombre, str) or self.nombre not in ROLES_INICIALES:
            raise ValueError("El rol no pertenece al catálogo aprobado.")
        if self.id_rol is not None and (
            type(self.id_rol) is not int or self.id_rol <= 0
        ):
            raise ValueError("id_rol debe ser un entero positivo.")
