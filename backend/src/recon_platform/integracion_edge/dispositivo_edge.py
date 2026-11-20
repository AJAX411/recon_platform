"""DispositivoEdge como entidad administrativa."""

from dataclasses import dataclass
from datetime import datetime

from recon_platform.accesos.punto_acceso import PuntoAcceso, texto

MODOS = frozenset({"ENTRADA", "SALIDA", "AUTOMATICO"})
ESTADOS = frozenset({"ACTIVO", "INACTIVO"})


@dataclass(kw_only=True, slots=True)
class DispositivoEdge:
    id_punto_acceso: int
    codigo: str
    nombre: str
    modo_operacion: str
    estado: str = "INACTIVO"
    ultima_comunicacion: datetime | None = None
    id_dispositivo: int | None = None
    fecha_creacion: datetime | None = None
    fecha_actualizacion: datetime | None = None

    def __post_init__(self) -> None:
        if type(self.id_punto_acceso) is not int or self.id_punto_acceso <= 0:
            raise ValueError("Punto obligatorio inválido.")
        if self.id_dispositivo is not None and (type(self.id_dispositivo) is not int or self.id_dispositivo <= 0):
            raise ValueError("ID de dispositivo inválido.")
        self.codigo = texto(self.codigo, 20)
        self.nombre = texto(self.nombre, 100)
        if (not isinstance(self.modo_operacion, str) or self.modo_operacion not in MODOS
            or not isinstance(self.estado, str) or self.estado not in ESTADOS):
            raise ValueError("Modo o estado de dispositivo inválido.")
        if self.ultima_comunicacion is not None and not isinstance(self.ultima_comunicacion, datetime):
            raise ValueError("Fecha de comunicación inválida.")


def permite_nueva_autorizacion(punto: PuntoAcceso, dispositivo: DispositivoEdge) -> bool:
    """Regla administrativa preparada para el futuro flujo de EventoAcceso."""
    if punto.id_punto_acceso is None or dispositivo.id_punto_acceso != punto.id_punto_acceso:
        return False
    return punto.estado == "ACTIVO" and dispositivo.estado == "ACTIVO"
