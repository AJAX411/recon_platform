"""Frontera HTTP de autenticación humana; la cookie solo porta un identificador."""

from flask import Blueprint, Response, current_app, jsonify, request

from recon_platform.identidad.servicios.limitador import LimitadorIntentos
from recon_platform.identidad.servicios.sesiones import token_csrf
from recon_platform.identidad.dto.autenticacion import representar_identidad, validar_login
from recon_platform.identidad.controladores import seguridad

bp = Blueprint("autenticacion", __name__, url_prefix="/api/v1/auth")

bp.before_request(seguridad.comprobar_transporte_web)


@bp.after_request
def _sin_cache(respuesta: Response) -> Response:
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


@bp.get("/csrf")
def obtener_csrf() -> Response | tuple[Response, int]:
    gestor = seguridad.gestor_actual()
    if gestor is None:
        return seguridad.respuesta_error(503, "La autenticación HTTP no está configurada.")
    ahora = seguridad.ahora_utc()
    token = request.cookies.get(seguridad.NOMBRE_COOKIE)
    try:
        sesion = gestor.obtener(token, ahora)
        if sesion is None or token is None:
            token = gestor.iniciar_anonima(ahora)
    except Exception:
        seguridad.revertir_sin_detalles()
        return seguridad.respuesta_error(503, "No se pudo preparar la sesión.")
    respuesta = jsonify({"csrf_token": token_csrf(token, gestor.clave_csrf)})
    seguridad.establecer_cookie(respuesta, token)
    return respuesta


@bp.post("/login")
def login() -> Response | tuple[Response, int]:
    gestor = seguridad.gestor_actual()
    if gestor is None:
        return seguridad.respuesta_error(503, "La autenticación HTTP no está configurada.")
    ahora = seguridad.ahora_utc()
    try:
        csrf_valido = seguridad.csrf_requerido(gestor, ahora)
    except seguridad.ServicioIAMNoDisponible:
        return seguridad.respuesta_error(503, "No se pudo comprobar la sesión.")
    if not csrf_valido:
        return seguridad.respuesta_error(403, "Token CSRF ausente o inválido.")
    cuerpo = request.get_json(silent=True)
    credenciales = validar_login(cuerpo)
    if credenciales is None:
        return seguridad.respuesta_error(400, "Solicitud de autenticación inválida.")
    usuario, contrasena = credenciales
    limitador: LimitadorIntentos = current_app.extensions["recon_limitador_login"]
    if not limitador.admitir(request.remote_addr or "desconocida", ahora):
        respuesta = jsonify({"error": "Demasiados intentos de autenticación."})
        respuesta.headers["Retry-After"] = "300"
        return respuesta, 429
    try:
        resultado = gestor.iniciar_autenticada(
            request.cookies[seguridad.NOMBRE_COOKIE], usuario, contrasena, ahora
        )
    except Exception:
        seguridad.revertir_sin_detalles()
        return seguridad.respuesta_error(503, "No se pudo completar la autenticación.")
    if resultado is None:
        return seguridad.respuesta_error(401, "Credenciales inválidas.")
    token_nuevo, identidad = resultado
    respuesta = jsonify(representar_identidad(identidad))
    respuesta.headers["X-CSRF-Token"] = token_csrf(token_nuevo, gestor.clave_csrf)
    seguridad.establecer_cookie(respuesta, token_nuevo)
    return respuesta


@bp.post("/logout")
def logout() -> Response | tuple[Response, int]:
    gestor = seguridad.gestor_actual()
    if gestor is None:
        return seguridad.respuesta_error(503, "La autenticación HTTP no está configurada.")
    ahora = seguridad.ahora_utc()
    try:
        csrf_valido = seguridad.csrf_requerido(gestor, ahora)
    except seguridad.ServicioIAMNoDisponible:
        return seguridad.respuesta_error(503, "No se pudo comprobar la sesión.")
    if not csrf_valido:
        return seguridad.respuesta_error(403, "Token CSRF ausente o inválido.")
    try:
        if not gestor.cerrar(request.cookies.get(seguridad.NOMBRE_COOKIE), ahora):
            return seguridad.respuesta_error(401, "No hay una sesión activa.")
    except Exception:
        seguridad.revertir_sin_detalles()
        return seguridad.respuesta_error(503, "No se pudo cerrar la sesión.")
    respuesta = jsonify({"estado": "cerrada"})
    respuesta.delete_cookie(
        seguridad.NOMBRE_COOKIE, path="/api/v1", httponly=True,
        secure=current_app.config["RECON_COOKIE_SECURE"], samesite="Lax",
    )
    return respuesta


@bp.get("/me")
def sesion_actual() -> Response | tuple[Response, int]:
    try:
        identidad = seguridad.identidad_http_actual()
    except seguridad.ServicioIAMNoDisponible:
        return seguridad.respuesta_error(503, "No se pudo comprobar la sesión.")
    if identidad is None:
        return seguridad.respuesta_error(401, "No hay una sesión activa.")
    return jsonify(representar_identidad(identidad))
