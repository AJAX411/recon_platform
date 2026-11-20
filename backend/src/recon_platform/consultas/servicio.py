"""Dashboard P0: permisos y corte único; ninguna escritura de negocio."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from recon_platform.accesos.evento_acceso import jornada_utc
from recon_platform.accesos.contratos_consultas import LecturaAccesos, ResumenAccesos
from recon_platform.consultas.contratos import UnidadLectura
from recon_platform.personas.contratos_consultas import LecturaPersonas


@dataclass(frozen=True, slots=True)
class Dashboard:
    reducido: bool
    corte: datetime
    inicio: datetime
    fin: datetime
    incidencias: dict[str, int]
    movimientos: list[dict]
    resumen: ResumenAccesos | None = None
    personas: int | None = None


class ConsultarDashboard:
    """Construye resumen por rol usando puertos de lectura y un corte temporal único."""
    def __init__(self, accesos: LecturaAccesos, personas: LecturaPersonas,
                 unidad: UnidadLectura, reloj: Callable[[], datetime]) -> None:
        self.accesos, self.personas, self.unidad, self.reloj = accesos, personas, unidad, reloj

    def ejecutar(self, *, rol: str) -> Dashboard:
        if rol not in {"SUPERADMIN", "ADMINISTRADOR", "OPERADOR"}:
            raise PermissionError("Consulta denegada.")
        self.unidad.iniciar()
        try:
            corte = self.reloj()
            if not isinstance(corte, datetime) or corte.tzinfo is None:
                raise ValueError("Reloj no disponible.")
            corte = corte.astimezone(UTC)
            inicio, fin = jornada_utc(corte)
            reducido = rol == "OPERADOR"
            incidencias = self.accesos.incidencias(inicio, fin, corte)
            movimientos = self.accesos.movimientos(inicio, fin, corte, reducido=reducido)
            # O no ejecuta consultas históricas ni de total de Personas.
            resumen = None if reducido else self.accesos.resumen(inicio, fin, corte)
            personas = None if reducido else self.personas.total()
            return Dashboard(reducido, corte, inicio, fin, incidencias, movimientos, resumen, personas)
        finally:
            self.unidad.terminar()
