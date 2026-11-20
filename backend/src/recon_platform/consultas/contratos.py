"""Límite de una lectura consistente compartida por capacidades."""

from typing import Protocol


class UnidadLectura(Protocol):
    def iniciar(self) -> None: ...
    def terminar(self) -> None: ...
