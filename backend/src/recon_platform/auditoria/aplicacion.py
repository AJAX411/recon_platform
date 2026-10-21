"""Registro interno y consulta autorizada de eventos generales."""

from datetime import datetime
from typing import Protocol

from recon_platform.auditoria.dominio import EventoAuditoria


class RepositorioEventos(Protocol):
    def agregar(self, evento: EventoAuditoria) -> EventoAuditoria: ...
    def listar(self, *, limite: int, desplazamiento: int, filtros: dict) -> list[EventoAuditoria]: ...


class UnidadTrabajo(Protocol):
    def confirmar(self) -> None: ...
    def revertir(self) -> None: ...


class AuditoriaGeneral:
    def __init__(self, repositorio: RepositorioEventos, unidad: UnidadTrabajo) -> None:
        self.repositorio, self.unidad = repositorio, unidad

    def registrar_fallo(self, *, actor_id: int, accion: str, recurso_tipo: str,
                       recurso_id: int | None = None, detalle: str) -> None:
        """Se invoca tras revertir la operación fallida; jamás confirma esa mutación."""
        try:
            self.repositorio.agregar(EventoAuditoria(
                id_usuario_actor=actor_id, accion=accion, resultado="FALLIDO",
                recurso_tipo=recurso_tipo,
                id_recurso_afectado=str(recurso_id) if recurso_id is not None else None,
                detalle=detalle,
            ))
            self.unidad.confirmar()
        except Exception:
            self.unidad.revertir()
            raise

    def listar(self, *, actor_id: int, rol: str, limite: int, desplazamiento: int,
               filtros: dict) -> list[EventoAuditoria]:
        if type(actor_id) is not int or actor_id <= 0 or rol not in {"SUPERADMIN", "ADMINISTRADOR"}:
            raise PermissionError("Consulta de auditoría denegada.")
        if type(limite) is not int or not 1 <= limite <= 100 or type(desplazamiento) is not int or not 0 <= desplazamiento <= 1_000_000:
            raise ValueError("Paginación inválida.")
        if set(filtros) - {"accion", "resultado", "recurso_tipo", "id_usuario_actor", "desde", "hasta"}:
            raise ValueError("Filtro inválido.")
        if any(not isinstance(filtros.get(c), datetime) or filtros[c].tzinfo is None
               for c in ("desde", "hasta") if c in filtros):
            raise ValueError("Fecha inválida.")
        if "desde" in filtros and "hasta" in filtros and filtros["desde"] > filtros["hasta"]:
            raise ValueError("Rango inválido.")
        return self.repositorio.listar(limite=limite, desplazamiento=desplazamiento, filtros=filtros)
