"""Vigencia de una sesión humana, independiente de Flask y MySQL."""

from dataclasses import dataclass
from datetime import datetime, timedelta

INACTIVIDAD = timedelta(minutes=30)
DURACION_MAXIMA = timedelta(hours=8)


@dataclass(slots=True)
class SesionUsuario:
    digest: str
    id_usuario: int | None
    fecha_creacion: datetime
    fecha_actividad: datetime
    fecha_expiracion: datetime
    fecha_revocacion: datetime | None = None

    def vigente(self, ahora: datetime) -> bool:
        return (
            self.fecha_revocacion is None
            and ahora < self.fecha_expiracion
            and ahora - self.fecha_actividad < INACTIVIDAD
        )
