"""Casos de uso de sesión humana: vigencia, CSRF, rotación y cierre.
Usa tokens aleatorios, digests y HMAC; consulta cuenta/rol actuales por puertos.
Los identificadores y credenciales no se registran en logs ni auditoría."""

import hashlib
import hmac
import re
import secrets
from datetime import datetime
from typing import TypeGuard

from recon_platform.identidad.servicio_cuentas import AutenticarUsuarioPlataforma, IdentidadAutenticada
from recon_platform.identidad.contratos_cuentas import RepositorioIAM, UnidadTrabajoIAM
from recon_platform.identidad.sesion import DURACION_MAXIMA, SesionUsuario
from recon_platform.identidad.contratos_sesiones import RepositorioSesiones

PATRON_TOKEN = re.compile(r"[A-Za-z0-9_-]{32,128}\Z")


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _token_valido(token: object) -> TypeGuard[str]:
    return isinstance(token, str) and PATRON_TOKEN.fullmatch(token) is not None


def token_csrf(token_sesion: str, clave: str) -> str:
    """Token ligado a una sesión; el servidor no persiste su valor en claro."""
    return hmac.new(
        clave.encode("utf-8"), b"recon-csrf-v1:" + token_sesion.encode("ascii"), hashlib.sha256
    ).hexdigest()


class GestionSesiones:
    """Coordina tokens opacos y cuenta vigente mediante puertos, sin Flask."""
    def __init__(
        self,
        sesiones: RepositorioSesiones,
        cuentas: RepositorioIAM,
        unidad: UnidadTrabajoIAM,
        clave_csrf: str,
    ) -> None:
        self.sesiones = sesiones
        self.cuentas = cuentas
        self.unidad = unidad
        self.clave_csrf = clave_csrf

    def obtener(self, token: object, ahora: datetime) -> SesionUsuario | None:
        if not _token_valido(token):
            return None
        sesion = self.sesiones.obtener(_digest(token))
        return sesion if sesion is not None and sesion.vigente(ahora) else None

    def csrf_valido(self, token: object, csrf: object, ahora: datetime) -> bool:
        return (
            isinstance(token, str)
            and self.obtener(token, ahora) is not None
            and isinstance(csrf, str)
            and len(csrf) == 64
            and hmac.compare_digest(token_csrf(token, self.clave_csrf), csrf)
        )

    def iniciar_anonima(self, ahora: datetime) -> str:
        return self._crear(None, ahora)

    def _crear(self, id_usuario: int | None, ahora: datetime) -> str:
        token = secrets.token_urlsafe(32)
        try:
            self.sesiones.guardar(SesionUsuario(
                digest=_digest(token), id_usuario=id_usuario,
                fecha_creacion=ahora, fecha_actividad=ahora,
                fecha_expiracion=ahora + DURACION_MAXIMA,
            ))
            self.unidad.confirmar()
        except Exception:
            self.unidad.revertir()
            raise
        return token

    def iniciar_autenticada(
        self, token_anterior: str, login: str, contrasena: str, ahora: datetime
    ) -> tuple[str, IdentidadAutenticada] | None:
        """Verifica credenciales y rota la sesión anterior solo tras autenticación válida."""
        anterior = self.obtener(token_anterior, ahora)
        if anterior is None:
            return None
        # El caso de uso existente mantiene la única verificación de credenciales.
        identidad = AutenticarUsuarioPlataforma(self.cuentas, self.unidad).ejecutar(
            login=login, contrasena=contrasena
        )
        if identidad is None:
            return None
        try:
            self.sesiones.revocar(anterior.digest, ahora)
            nuevo = self._crear(identidad.id_usuario, ahora)
            return nuevo, identidad
        except Exception:
            self.unidad.revertir()
            raise

    def identidad_actual(self, token: object, ahora: datetime) -> IdentidadAutenticada | None:
        """Relee estado/rol de la cuenta y renueva actividad de una sesión vigente."""
        sesion = self.obtener(token, ahora)
        if sesion is None or sesion.id_usuario is None:
            return None
        cuenta = self.cuentas.obtener_por_id(sesion.id_usuario)
        if cuenta is None or cuenta.estado != "ACTIVO" or cuenta.id_usuario is None:
            return None
        identidad = IdentidadAutenticada(
            id_usuario=cuenta.id_usuario, login=cuenta.login, rol_nombre=cuenta.rol.nombre
        )
        if ahora > sesion.fecha_actividad:
            try:
                self.sesiones.actualizar_actividad(sesion.digest, ahora)
                self.unidad.confirmar()
            except Exception:
                self.unidad.revertir()
                raise
        return identidad

    def cerrar(self, token: object, ahora: datetime) -> bool:
        sesion = self.obtener(token, ahora)
        if sesion is None or sesion.id_usuario is None:
            return False
        try:
            self.sesiones.revocar(sesion.digest, ahora)
            self.unidad.confirmar()
        except Exception:
            self.unidad.revertir()
            raise
        return True
