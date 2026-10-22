"""Reglas funcionales de EventoAcceso; independientes de HTTP y persistencia."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

MOVIMIENTOS = frozenset({"ENTRADA", "SALIDA"})
RESULTADOS = frozenset({"AUTORIZADO", "RECHAZADO"})
METODOS = frozenset({"MANUAL", "FACIAL"})
INCIDENCIAS = frozenset({
    "ENTRADA_REPETIDA", "SALIDA_REPETIDA", "SALIDA_SIN_ENTRADA_DEL_DIA",
})
BOGOTA = ZoneInfo("America/Bogota")


def jornada_utc(instante: datetime) -> tuple[datetime, datetime]:
    """Intervalo UTC cerrado por la izquierda para el día civil de Bogotá."""
    if not isinstance(instante, datetime) or instante.tzinfo is None:
        raise ValueError("Se requiere un instante con zona horaria.")
    fecha = instante.astimezone(BOGOTA).date()
    inicio = datetime.combine(fecha, datetime.min.time(), tzinfo=BOGOTA)
    siguiente = datetime.combine(fecha + timedelta(days=1), datetime.min.time(), tzinfo=BOGOTA)
    return inicio.astimezone(UTC), siguiente.astimezone(UTC)


def incidencia_secuencia(ultimo_autorizado: str | None, nuevo: str) -> str | None:
    if nuevo not in MOVIMIENTOS or ultimo_autorizado not in MOVIMIENTOS | {None}:
        raise ValueError("Movimiento inválido.")
    if ultimo_autorizado is None:
        return "SALIDA_SIN_ENTRADA_DEL_DIA" if nuevo == "SALIDA" else None
    if ultimo_autorizado == nuevo:
        return "ENTRADA_REPETIDA" if nuevo == "ENTRADA" else "SALIDA_REPETIDA"
    return None


@dataclass(frozen=True, slots=True, kw_only=True)
class EventoAcceso:
    id_persona: int | None
    id_punto_acceso: int
    tipo_movimiento: str
    resultado: str
    metodo_registro: str
    id_usuario_registrador: int | None
    fecha_hora_ocurrencia: datetime
    tipo_incidencia_secuencia: str | None = None
    id_dispositivo: int | None = None
    clave_idempotencia: str | None = None
    id_evento_acceso: int | None = None

    def __post_init__(self) -> None:
        for identificador in (self.id_persona, self.id_usuario_registrador,
                              self.id_dispositivo, self.id_evento_acceso):
            if identificador is not None and (type(identificador) is not int or identificador <= 0):
                raise ValueError("Identificador inválido.")
        if type(self.id_punto_acceso) is not int or self.id_punto_acceso <= 0:
            raise ValueError("Punto inválido.")
        if (self.tipo_movimiento not in MOVIMIENTOS or self.resultado not in RESULTADOS
            or self.metodo_registro not in METODOS
            or self.tipo_incidencia_secuencia not in INCIDENCIAS | {None}):
            raise ValueError("Clasificación de evento inválida.")
        if self.fecha_hora_ocurrencia.tzinfo is None:
            raise ValueError("La hora debe ser UTC con zona.")
        if self.metodo_registro == "MANUAL" and (
            self.id_persona is None or self.id_usuario_registrador is None
            or self.id_dispositivo is not None or self.clave_idempotencia is None
        ):
            raise ValueError("Origen manual inválido.")
        if self.tipo_incidencia_secuencia is not None and self.resultado != "AUTORIZADO":
            raise ValueError("Un rechazo no tiene incidencia de secuencia.")
