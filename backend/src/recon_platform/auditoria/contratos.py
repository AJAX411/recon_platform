"""Puertos de aplicación existentes."""

from typing import Protocol

from recon_platform.auditoria.evento_auditoria import EventoAuditoria


class RepositorioEventos(Protocol):
    def agregar(self, evento: EventoAuditoria) -> EventoAuditoria: ...
    def listar(self, *, limite: int, desplazamiento: int, filtros: dict) -> list[EventoAuditoria]: ...


class UnidadTrabajo(Protocol):
    def confirmar(self) -> None: ...
    def revertir(self) -> None: ...
