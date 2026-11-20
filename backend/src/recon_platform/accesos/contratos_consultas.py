"""Puerto público de lectura para reporting, sin exponer repositorios ORM."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ResumenAccesos:
    entradas: int
    salidas: int
    dentro: int
    personas_con_historial: int


class LecturaAccesos(Protocol):
    def resumen(self, inicio: datetime, fin: datetime, corte: datetime) -> ResumenAccesos: ...
    def incidencias(self, inicio: datetime, fin: datetime, corte: datetime) -> dict[str, int]: ...
    def movimientos(self, inicio: datetime, fin: datetime, corte: datetime,
                    *, reducido: bool) -> list[dict]: ...
