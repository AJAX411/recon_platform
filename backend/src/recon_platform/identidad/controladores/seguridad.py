"""Adaptador HTTP de sesión, CSRF, roles y transporte."""

from datetime import UTC, datetime
from functools import wraps
from typing import Callable

from flask import Response, current_app, g, jsonify, request

from recon_platform.extensions import db
from recon_platform.identidad.servicios.cuentas import IdentidadAutenticada
from recon_platform.identidad.servicios.sesiones import GestionSesiones
from recon_platform.composicion import crear_gestor_sesiones

NOMBRE_COOKIE = "recon_session"


class ServicioIAMNoDisponible(Exception):
    """No fue posible comprobar la sesión por un fallo interno."""


def revertir_sin_detalles() -> None:
    try:
        db.session.rollback()
    except Exception:
        pass  # No incorporar detalles del controlador a la respuesta HTTP.


def ahora_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def gestor_actual() -> GestionSesiones | None:
    clave = current_app.config.get("SECRET_KEY")
    if (
        not isinstance(clave, str) or len(clave.encode("utf-8")) < 32
        or "sqlalchemy" not in current_app.extensions
    ):
        return None
    return crear_gestor_sesiones(clave)


def respuesta_error(codigo: int, mensaje: str) -> tuple[Response, int]:
    return jsonify({"error": mensaje}), codigo


def establecer_cookie(respuesta: Response, token: str) -> None:
    respuesta.set_cookie(
        NOMBRE_COOKIE, token, max_age=8 * 60 * 60,
        httponly=True, secure=current_app.config["RECON_COOKIE_SECURE"],
        samesite="Lax", path="/api/v1",
    )


def comprobar_transporte_web() -> tuple[Response, int] | None:
    request.max_content_length = 16 * 1024
    if current_app.config["RECON_COOKIE_SECURE"] and not request.is_secure:
        return respuesta_error(403, "La autenticación HTTP requiere HTTPS.")
    if (
        not current_app.config["RECON_COOKIE_SECURE"]
        and (
            request.host.split(":", 1)[0] not in {"127.0.0.1", "localhost"}
            or request.remote_addr not in {"127.0.0.1", "::1"}
        )
    ):
        return respuesta_error(403, "El modo HTTP local solo acepta el host local.")
    return None


def csrf_requerido(gestor: GestionSesiones, ahora: datetime) -> bool:
    try:
        return gestor.csrf_valido(
            request.cookies.get(NOMBRE_COOKIE), request.headers.get("X-CSRF-Token"), ahora
        )
    except Exception:
        revertir_sin_detalles()
        raise ServicioIAMNoDisponible from None


def identidad_http_actual() -> IdentidadAutenticada | None:
    """Consulta cuenta y rol vigentes; sirve a los guards de futuras rutas IAM."""
    gestor = gestor_actual()
    if gestor is None:
        raise ServicioIAMNoDisponible
    try:
        return gestor.identidad_actual(request.cookies.get(NOMBRE_COOKIE), ahora_utc())
    except Exception:
        revertir_sin_detalles()
        raise ServicioIAMNoDisponible from None


def requerir_roles(*roles: str, al_denegar: Callable | None = None) -> Callable:
    """Guard de presentación; los casos de uso siguen validando al actor."""
    def decorar(vista: Callable) -> Callable:
        @wraps(vista)
        def protegida(*args: object, **kwargs: object) -> Response | tuple[Response, int]:
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                gestor = gestor_actual()
                if gestor is None:
                    return respuesta_error(503, "La autenticación HTTP no está configurada.")
                try:
                    csrf_valido = csrf_requerido(gestor, ahora_utc())
                except ServicioIAMNoDisponible:
                    return respuesta_error(503, "No se pudo comprobar la sesión.")
                if not csrf_valido:
                    return respuesta_error(403, "Token CSRF ausente o inválido.")
            try:
                identidad = identidad_http_actual()
            except ServicioIAMNoDisponible:
                return respuesta_error(503, "No se pudo comprobar la sesión.")
            if identidad is None:
                return respuesta_error(401, "No hay una sesión activa.")
            if identidad.rol_nombre not in roles:
                if al_denegar is not None:
                    try:
                        al_denegar(identidad, *args, **kwargs)
                    except Exception:
                        revertir_sin_detalles()
                        return respuesta_error(503, "No se pudo registrar la denegación administrativa.")
                return respuesta_error(403, "Permiso denegado.")
            g.identidad_iam = identidad
            return vista(*args, **kwargs)
        return protegida
    return decorar
