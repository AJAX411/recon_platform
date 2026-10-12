"""Contratos que los casos de uso esperan de la persistencia."""

from typing import Protocol

from recon_platform.personas.dominio.persona import Persona
from recon_platform.personas.dominio.tipo_persona import TipoPersona


class RepositorioTiposPersona(Protocol):
    def obtener_por_nombre(self, nombre: str) -> TipoPersona | None: ...


class RepositorioPersonas(Protocol):
    def existe_documento(self, tipo: str, numero: str) -> bool: ...

    def existe_identificador_institucional(self, identificador: str) -> bool: ...

    def agregar(self, persona: Persona) -> Persona: ...

    def obtener_por_id(self, id_persona: int) -> Persona | None: ...


class UnidadTrabajo(Protocol):
    def confirmar(self) -> None: ...

    def revertir(self) -> None: ...
