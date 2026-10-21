"""Frontera HTTP de autenticación humana; la cookie solo porta un identificador."""

from datetime import UTC, datetime
from functools import wraps
from typing import Callable

from flask import Blueprint, Response, current_app, g, jsonify, request

from recon_platform.extensions import db
from recon_platform.identidad.aplicacion.casos_de_uso import IdentidadAutenticada
from recon_platform.identidad.aplicacion.limitador import LimitadorIntentos
from recon_platform.identidad.aplicacion.sesiones import GestionSesiones, token_csrf
from recon_platform.identidad.infraestructura.repositorios import RepositorioIAMSQLAlchemy
from recon_platform.identidad.infraestructura.sesiones import RepositorioSesionesSQLAlchemy
from recon_platform.identidad.infraestructura.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy

bp = Blueprint("autenticacion", __name__, url_prefix="/api/v1/auth")
NOMBRE_COOKIE = "recon_session"


class ServicioIAMNoDisponible(Exception):
    """No fue posible comprobar la sesión por un fallo interno."""


def _revertir_sin_detalles() -> None:
    try:
        db.session.rollback()
    except Exception:
        pass  # No incorporar detalles del controlador a la respuesta HTTP.


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _gestor() -> GestionSesiones | None:
    clave = current_app.config.get("SECRET_KEY")
    if (
        not isinstance(clave, str) or len(clave.encode("utf-8")) < 32
        or "sqlalchemy" not in current_app.extensions
    ):
        return None
    return GestionSesiones(
        RepositorioSesionesSQLAlchemy(db.session),
        RepositorioIAMSQLAlchemy(db.session),
        UnidadTrabajoIAMSQLAlchemy(db.session),
        clave,
    )


def _error(codigo: int, mensaje: str) -> tuple[Response, int]:
    return jsonify({"error": mensaje}), codigo


def _cookie(respuesta: Response, token: str) -> None:
    respuesta.set_cookie(
        NOMBRE_COOKIE, token, max_age=8 * 60 * 60,
        httponly=True, secure=current_app.config["RECON_COOKIE_SECURE"],
        samesite="Lax", path="/api/v1",
    )


@bp.before_request
def _comprobar_host_local() -> tuple[Response, int] | None:
    request.max_content_length = 16 * 1024
    if current_app.config["RECON_COOKIE_SECURE"] and not request.is_secure:
        return _error(403, "La autenticación HTTP requiere HTTPS.")
    if (
        not current_app.config["RECON_COOKIE_SECURE"]
        and (
            request.host.split(":", 1)[0] not in {"127.0.0.1", "localhost"}
            or request.remote_addr not in {"127.0.0.1", "::1"}
        )
    ):
        return _error(403, "El modo HTTP local solo acepta el host local.")
    return None


@bp.after_request
def _sin_cache(respuesta: Response) -> Response:
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


@bp.get("/csrf")
def obtener_csrf() -> Response | tuple[Response, int]:
    gestor = _gestor()
    if gestor is None:
        return _error(503, "La autenticación HTTP no está configurada.")
    ahora = _ahora()
    token = request.cookies.get(NOMBRE_COOKIE)
    try:
        if gestor.obtener(token, ahora) is None:
            token = gestor.iniciar_anonima(ahora)
    except Exception:
        _revertir_sin_detalles()
        return _error(503, "No se pudo preparar la sesión.")
    respuesta = jsonify({"csrf_token": token_csrf(token, gestor.clave_csrf)})
    _cookie(respuesta, token)
    return respuesta


def _csrf_requerido(gestor: GestionSesiones, ahora: datetime) -> bool:
    try:
        return gestor.csrf_valido(
            request.cookies.get(NOMBRE_COOKIE), request.headers.get("X-CSRF-Token"), ahora
        )
    except Exception:
        _revertir_sin_detalles()
        raise ServicioIAMNoDisponible from None


@bp.post("/login")
def login() -> Response | tuple[Response, int]:
    gestor = _gestor()
    if gestor is None:
        return _error(503, "La autenticación HTTP no está configurada.")
    ahora = _ahora()
    try:
        csrf_valido = _csrf_requerido(gestor, ahora)
    except ServicioIAMNoDisponible:
        return _error(503, "No se pudo comprobar la sesión.")
    if not csrf_valido:
        return _error(403, "Token CSRF ausente o inválido.")
    cuerpo = request.get_json(silent=True)
    if not isinstance(cuerpo, dict):
        return _error(400, "Solicitud de autenticación inválida.")
    usuario, contrasena = cuerpo.get("login"), cuerpo.get("contrasena")
    if not isinstance(usuario, str) or not isinstance(contrasena, str):
        return _error(400, "Solicitud de autenticación inválida.")
    limitador: LimitadorIntentos = current_app.extensions["recon_limitador_login"]
    if not limitador.admitir(request.remote_addr or "desconocida", ahora):
        respuesta = jsonify({"error": "Demasiados intentos de autenticación."})
        respuesta.headers["Retry-After"] = "300"
        return respuesta, 429
    try:
        resultado = gestor.iniciar_autenticada(
            request.cookies[NOMBRE_COOKIE], usuario, contrasena, ahora
        )
    except Exception:
        _revertir_sin_detalles()
        return _error(503, "No se pudo completar la autenticación.")
    if resultado is None:
        return _error(401, "Credenciales inválidas.")
    token_nuevo, identidad = resultado
    respuesta = jsonify(_representar(identidad))
    respuesta.headers["X-CSRF-Token"] = token_csrf(token_nuevo, gestor.clave_csrf)
    _cookie(respuesta, token_nuevo)
    return respuesta


@bp.post("/logout")
def logout() -> Response | tuple[Response, int]:
    gestor = _gestor()
    if gestor is None:
        return _error(503, "La autenticación HTTP no está configurada.")
    ahora = _ahora()
    try:
        csrf_valido = _csrf_requerido(gestor, ahora)
    except ServicioIAMNoDisponible:
        return _error(503, "No se pudo comprobar la sesión.")
    if not csrf_valido:
        return _error(403, "Token CSRF ausente o inválido.")
    try:
        if not gestor.cerrar(request.cookies.get(NOMBRE_COOKIE), ahora):
            return _error(401, "No hay una sesión activa.")
    except Exception:
        _revertir_sin_detalles()
        return _error(503, "No se pudo cerrar la sesión.")
    respuesta = jsonify({"estado": "cerrada"})
    respuesta.delete_cookie(
        NOMBRE_COOKIE, path="/api/v1", httponly=True,
        secure=current_app.config["RECON_COOKIE_SECURE"], samesite="Lax",
    )
    return respuesta


def _representar(identidad: IdentidadAutenticada) -> dict[str, int | str]:
    return {
        "id_usuario": identidad.id_usuario,
        "login": identidad.login,
        "rol": identidad.rol_nombre,
    }


def identidad_http_actual() -> IdentidadAutenticada | None:
    """Consulta cuenta y rol vigentes; sirve a los guards de futuras rutas IAM."""
    gestor = _gestor()
    if gestor is None:
        raise ServicioIAMNoDisponible
    try:
        return gestor.identidad_actual(request.cookies.get(NOMBRE_COOKIE), _ahora())
    except Exception:
        _revertir_sin_detalles()
        raise ServicioIAMNoDisponible from None


def requerir_roles(*roles: str, al_denegar: Callable | None = None) -> Callable:
    """Guard de presentación; los casos de uso siguen validando al actor."""
    def decorar(vista: Callable) -> Callable:
        @wraps(vista)
        def protegida(*args: object, **kwargs: object) -> Response | tuple[Response, int]:
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                gestor = _gestor()
                if gestor is None:
                    return _error(503, "La autenticación HTTP no está configurada.")
                try:
                    csrf_valido = _csrf_requerido(gestor, _ahora())
                except ServicioIAMNoDisponible:
                    return _error(503, "No se pudo comprobar la sesión.")
                if not csrf_valido:
                    return _error(403, "Token CSRF ausente o inválido.")
            try:
                identidad = identidad_http_actual()
            except ServicioIAMNoDisponible:
                return _error(503, "No se pudo comprobar la sesión.")
            if identidad is None:
                return _error(401, "No hay una sesión activa.")
            if identidad.rol_nombre not in roles:
                if al_denegar is not None:
                    try:
                        al_denegar(identidad, *args, **kwargs)
                    except Exception:
                        _revertir_sin_detalles()
                        return _error(503, "No se pudo registrar la denegación administrativa.")
                return _error(403, "Permiso denegado.")
            g.identidad_iam = identidad
            return vista(*args, **kwargs)
        return protegida
    return decorar


@bp.get("/me")
def sesion_actual() -> Response | tuple[Response, int]:
    try:
        identidad = identidad_http_actual()
    except ServicioIAMNoDisponible:
        return _error(503, "No se pudo comprobar la sesión.")
    if identidad is None:
        return _error(401, "No hay una sesión activa.")
    return jsonify(_representar(identidad))
