"""Consulta restringida de eventos generales."""

from datetime import UTC, datetime

from flask import Blueprint, Response, g, jsonify

from recon_platform.composicion import auditoria
from recon_platform.http.administrativo import ejecutar, paginacion, registrar_denegacion
from recon_platform.identidad.seguridad_http import comprobar_transporte_web, requerir_roles
from recon_platform.auditoria.dto import representar_auditoria

bp = Blueprint("auditoria_general", __name__, url_prefix="/api/v1/auditoria")

bp.before_request(comprobar_transporte_web)


@bp.after_request
def _sin_cache(respuesta: Response) -> Response:
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


@bp.get("/eventos")
@requerir_roles("SUPERADMIN", "ADMINISTRADOR", al_denegar=lambda identidad:
    registrar_denegacion(identidad, accion="CONSULTAR_AUDITORIA", recurso_tipo="EVENTO_AUDITORIA"))
def listar_eventos():
    def operacion():
        limite, desplazamiento, filtros_texto = paginacion({
            "accion", "resultado", "recurso_tipo", "id_usuario_actor", "desde", "hasta"})
        filtros: dict[str, str | int | datetime] = dict(filtros_texto)
        for campo, maximo in (("accion", 50), ("recurso_tipo", 50)):
            if campo in filtros_texto and (not filtros_texto[campo].strip() or len(filtros_texto[campo]) > maximo):
                raise ValueError("Filtro inválido.")
        if "resultado" in filtros_texto and filtros_texto["resultado"] not in {"EXITOSO", "FALLIDO"}:
            raise ValueError("Resultado inválido.")
        if "id_usuario_actor" in filtros_texto:
            valor = filtros_texto["id_usuario_actor"]
            if not valor.isdecimal() or len(valor) > 10 or int(valor) <= 0:
                raise ValueError("Actor inválido.")
            filtros["id_usuario_actor"] = int(valor)
        for campo in ("desde", "hasta"):
            if campo in filtros_texto:
                try:
                    fecha = datetime.fromisoformat(filtros_texto[campo])
                except ValueError as error:
                    raise ValueError("Fecha inválida.") from error
                if fecha.tzinfo is None:
                    raise ValueError("Fecha sin zona horaria.")
                filtros[campo] = fecha.astimezone(UTC)
        eventos = auditoria().listar(actor_id=g.identidad_iam.id_usuario,
            rol=g.identidad_iam.rol_nombre, limite=limite, desplazamiento=desplazamiento,
            filtros=filtros)
        return jsonify({"eventos": [representar_auditoria(e) for e in eventos],
                        "limite": limite, "desplazamiento": desplazamiento})
    return ejecutar(operacion)
