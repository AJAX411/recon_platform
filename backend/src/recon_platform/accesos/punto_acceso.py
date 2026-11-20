"""PuntoAcceso: ubicación administrativa, sin decisiones de EventoAcceso."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, overload


@overload
def texto(valor: object, maximo: int, *, opcional: Literal[False] = False) -> str: ...


@overload
def texto(valor: object, maximo: int, *, opcional: Literal[True]) -> str | None: ...


@overload
def texto(valor: object, maximo: int, *, opcional: bool) -> str | None: ...


def texto(valor: object, maximo: int, *, opcional: bool = False) -> str | None:
    if valor is None and opcional:
        return None
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError("Texto obligatorio inválido.")
    limpio = valor.strip()
    if len(limpio) > maximo or any(ord(c) < 32 for c in limpio):
        raise ValueError("Longitud o caracteres inválidos.")
    return limpio


@dataclass(kw_only=True, slots=True)
class PuntoAcceso:
    codigo: str
    nombre: str
    descripcion: str | None = None
    estado: str = "ACTIVO"
    id_punto_acceso: int | None = None
    fecha_creacion: datetime | None = None
    fecha_actualizacion: datetime | None = None

    def __post_init__(self) -> None:
        self.codigo = texto(self.codigo, 20)
        self.nombre = texto(self.nombre, 100)
        self.descripcion = texto(self.descripcion, 150, opcional=True)
        if not isinstance(self.estado, str) or self.estado not in {"ACTIVO", "INACTIVO"}:
            raise ValueError("Estado de punto inválido.")
        if self.id_punto_acceso is not None and (type(self.id_punto_acceso) is not int or self.id_punto_acceso <= 0):
            raise ValueError("ID de punto inválido.")
