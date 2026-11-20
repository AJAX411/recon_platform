"""Límite local y acotado de intentos HTTP; no almacena credenciales."""

from collections import deque
from datetime import datetime, timedelta
from threading import Lock


class LimitadorIntentos:
    """Máximo diez intentos por dirección remota en cinco minutos por proceso."""

    VENTANA = timedelta(minutes=5)
    MAXIMO = 10
    DIRECCIONES_MAXIMAS = 4096

    def __init__(self) -> None:
        self._intentos: dict[str, deque[datetime]] = {}
        self._candado = Lock()

    def admitir(self, direccion: str, ahora: datetime) -> bool:
        with self._candado:
            if len(self._intentos) >= self.DIRECCIONES_MAXIMAS:
                self._intentos = {
                    clave: marcas for clave, marcas in self._intentos.items()
                    if marcas and ahora - marcas[-1] < self.VENTANA
                }
                if len(self._intentos) >= self.DIRECCIONES_MAXIMAS:
                    mas_antigua = min(self._intentos, key=lambda clave: self._intentos[clave][-1])
                    del self._intentos[mas_antigua]
            marcas = self._intentos.setdefault(direccion, deque())
            while marcas and ahora - marcas[0] >= self.VENTANA:
                marcas.popleft()
            if len(marcas) >= self.MAXIMO:
                return False
            marcas.append(ahora)
            return True
