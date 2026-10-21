"""Evento de auditoría independiente de HTTP y persistencia."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EventoAuditoria:
    accion: str
    resultado: str
    tipo_actor: str = "USUARIO"
    id_usuario_actor: int | None = None
    recurso_tipo: str | None = None
    id_recurso_afectado: str | None = None
    detalle: str | None = None
    fecha_hora: datetime | None = None
    id_auditoria: int | None = None

    def __post_init__(self) -> None:
        if self.tipo_actor not in {"USUARIO", "SISTEMA"}:
            raise ValueError("Tipo de actor inválido.")
        if (self.tipo_actor == "USUARIO") != (type(self.id_usuario_actor) is int and self.id_usuario_actor > 0):
            raise ValueError("Actor incompatible con el tipo de evento.")
        if self.resultado not in {"EXITOSO", "FALLIDO"}:
            raise ValueError("Resultado de auditoría inválido.")
        for valor, maximo in ((self.accion, 50), (self.recurso_tipo, 50),
                              (self.id_recurso_afectado, 100)):
            if valor is not None and (not isinstance(valor, str) or not valor or len(valor) > maximo):
                raise ValueError("Campo de auditoría inválido.")
        if not isinstance(self.accion, str) or not self.accion:
            raise ValueError("La acción es obligatoria.")
        if self.detalle is not None and not isinstance(self.detalle, str):
            raise ValueError("Detalle de auditoría inválido.")
