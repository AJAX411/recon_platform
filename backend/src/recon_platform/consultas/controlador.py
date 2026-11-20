"""Endpoint aditivo P0 sin filtros ni acceso a datos Edge."""

from datetime import UTC, datetime

from flask import Blueprint, g, jsonify, request

from recon_platform.composicion import crear_dashboard
from recon_platform.consultas.dto import representar_dashboard
from recon_platform.identidad.seguridad_http import comprobar_transporte_web, requerir_roles

bp = Blueprint("consultas", __name__, url_prefix="/api/v1/consultas")
bp.before_request(comprobar_transporte_web)


def _reloj() -> datetime:
    return datetime.now(UTC)


@bp.after_request
def sin_cache(respuesta):
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


@bp.get("/dashboard")
@requerir_roles("SUPERADMIN", "ADMINISTRADOR", "OPERADOR")
def dashboard():
    if request.args:
        return jsonify({"error": "El dashboard no admite parámetros."}), 400
    try:
        return jsonify(representar_dashboard(
            crear_dashboard(_reloj).ejecutar(rol=g.identidad_iam.rol_nombre)))
    except PermissionError:
        return jsonify({"error": "Permiso denegado."}), 403
    except Exception:
        return jsonify({"error": "El resumen de la plataforma no está disponible."}), 503
