"""Consulta pública agregada; no concede acceso al catálogo administrativo."""

from typing import Protocol


class LecturaPersonas(Protocol):
    def total(self) -> int: ...
