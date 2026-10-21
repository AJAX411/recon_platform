"""Consulta restringida de eventos generales."""

from datetime import UTC, datetime

from flask import Blueprint, Response, g, jsonify

from recon_platform.composicion_administrativa import auditoria
from recon_platform.http_administrativo import ejecutar, paginacion, registrar_denegacion
from recon_platform.identidad.api import _comprobar_host_local, requerir_roles

bp = Blueprint("auditoria_general", __name__, url_prefix="/api/v1/auditoria")
bp.before_request(_comprobar_host_local)


@bp.after_request
def _sin_cache(respuesta: Response) -> Response:
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


def _representar(e) -> dict:
    return {"id_auditoria": e.id_auditoria, "id_usuario_actor": e.id_usuario_actor,
            "tipo_actor": e.tipo_actor, "accion": e.accion, "recurso_tipo": e.recurso_tipo,
            "id_recurso_afectado": e.id_recurso_afectado, "resultado": e.resultado,
            "detalle": e.detalle, "fecha_hora": e.fecha_hora.isoformat()}


@bp.get("/eventos")
@requerir_roles("SUPERADMIN", "ADMINISTRADOR", al_denegar=lambda identidad:
    registrar_denegacion(identidad, accion="CONSULTAR_AUDITORIA", recurso_tipo="EVENTO_AUDITORIA"))
def listar_eventos():
    def operacion():
        limite, desplazamiento, filtros = paginacion({
            "accion", "resultado", "recurso_tipo", "id_usuario_actor", "desde", "hasta"})
        for campo, maximo in (("accion", 50), ("recurso_tipo", 50)):
            if campo in filtros and (not filtros[campo].strip() or len(filtros[campo]) > maximo):
                raise ValueError("Filtro inválido.")
        if "resultado" in filtros and filtros["resultado"] not in {"EXITOSO", "FALLIDO"}:
            raise ValueError("Resultado inválido.")
        if "id_usuario_actor" in filtros:
            valor = filtros["id_usuario_actor"]
            if not valor.isdecimal() or len(valor) > 10 or int(valor) <= 0:
                raise ValueError("Actor inválido.")
            filtros["id_usuario_actor"] = int(valor)
        for campo in ("desde", "hasta"):
            if campo in filtros:
                try:
                    fecha = datetime.fromisoformat(filtros[campo])
                except ValueError as error:
                    raise ValueError("Fecha inválida.") from error
                if fecha.tzinfo is None:
                    raise ValueError("Fecha sin zona horaria.")
                filtros[campo] = fecha.astimezone(UTC)
        eventos = auditoria().listar(actor_id=g.identidad_iam.id_usuario,
            rol=g.identidad_iam.rol_nombre, limite=limite, desplazamiento=desplazamiento,
            filtros=filtros)
        return jsonify({"eventos": [_representar(e) for e in eventos],
                        "limite": limite, "desplazamiento": desplazamiento})
    return ejecutar(operacion)
