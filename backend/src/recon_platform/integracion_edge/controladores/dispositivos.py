"""API web administrativa de DispositivoEdge; no es contrato de la Raspberry."""

import json

from flask import Blueprint, Response, g, jsonify, request

from recon_platform.composicion import dispositivos
from recon_platform.http.administrativo import (
    cuerpo,
    ejecutar,
    paginacion,
    registrar_denegacion,
    sin_parametros,
)
from recon_platform.identidad.controladores.seguridad import comprobar_transporte_web, requerir_roles
from recon_platform.integracion_edge.dominio.dispositivo_edge import DispositivoEdge, MODOS
from recon_platform.integracion_edge.dto.dispositivos import representar_dispositivo

bp = Blueprint("dispositivos_edge", __name__, url_prefix="/api/v1/dispositivos-edge")

bp.before_request(comprobar_transporte_web)

TODOS = ("SUPERADMIN", "ADMINISTRADOR", "OPERADOR")
ADMIN = ("SUPERADMIN", "ADMINISTRADOR")


@bp.after_request
def _sin_cache(respuesta: Response) -> Response:
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


def _actor() -> tuple[int, str]:
    return g.identidad_iam.id_usuario, g.identidad_iam.rol_nombre


def _denegacion(accion: str):
    def registrar(identidad, id_dispositivo: int | None = None):
        registrar_denegacion(identidad, accion=accion, recurso_tipo="DISPOSITIVO_EDGE",
                             recurso_id=id_dispositivo)
    return registrar


def _detalle_modo_fallido(id_dispositivo: int, motivo: str) -> str:
    anterior = None
    try:
        d = dispositivos().dispositivos.obtener(id_dispositivo)
        if d is not None:
            anterior = d.modo_operacion
    except Exception:
        pass
    datos = request.get_json(silent=True)
    nuevo = datos.get("modo_operacion") if isinstance(datos, dict) else None
    if not isinstance(nuevo, str) or nuevo not in MODOS:
        nuevo = None
    return json.dumps({"anterior": anterior, "nuevo": nuevo, "motivo": motivo}, separators=(",", ":"))


@bp.get("")
@requerir_roles(*TODOS)
def listar_dispositivos():
    def operacion():
        limite, desplazamiento, filtros_texto = paginacion({"codigo", "estado", "modo_operacion", "id_punto_acceso"})
        filtros: dict[str, str | int] = dict(filtros_texto)
        if "id_punto_acceso" in filtros_texto:
            valor = filtros_texto["id_punto_acceso"]
            if not valor.isdecimal() or len(valor) > 10:
                raise ValueError("Punto inválido.")
            filtros["id_punto_acceso"] = int(valor)
        actor_id, rol = _actor()
        lista = dispositivos().listar(actor_id=actor_id, rol=rol, limite=limite,
                                      desplazamiento=desplazamiento, filtros=filtros)
        return jsonify({"dispositivos": [representar_dispositivo(d) for d in lista],
                        "limite": limite, "desplazamiento": desplazamiento})
    return ejecutar(operacion)


@bp.get("/<int:id_dispositivo>")
@requerir_roles(*TODOS)
def consultar_dispositivo(id_dispositivo: int):
    def operacion():
        sin_parametros()
        actor_id, rol = _actor()
        return jsonify(representar_dispositivo(dispositivos().consultar(actor_id=actor_id, rol=rol,
                                                              id_dispositivo=id_dispositivo)))
    return ejecutar(operacion)


@bp.post("")
@requerir_roles(*ADMIN, al_denegar=_denegacion("CREAR_DISPOSITIVO_EDGE"))
def crear_dispositivo():
    def operacion():
        sin_parametros()
        datos = cuerpo({"id_punto_acceso", "codigo", "nombre", "modo_operacion"},
                       obligatorios={"id_punto_acceso", "codigo", "nombre", "modo_operacion"})
        actor_id, rol = _actor()
        guardado = dispositivos().crear(actor_id=actor_id, rol=rol, dispositivo=DispositivoEdge(**datos))
        respuesta = jsonify(representar_dispositivo(guardado))
        respuesta.headers["Location"] = f"/api/v1/dispositivos-edge/{guardado.id_dispositivo}"
        return respuesta, 201
    return ejecutar(operacion, accion="CREAR_DISPOSITIVO_EDGE", recurso_tipo="DISPOSITIVO_EDGE")


@bp.patch("/<int:id_dispositivo>")
@requerir_roles(*ADMIN, al_denegar=_denegacion("EDITAR_DISPOSITIVO_EDGE"))
def editar_dispositivo(id_dispositivo: int):
    def operacion():
        sin_parametros()
        datos = cuerpo({"nombre"}, obligatorios={"nombre"})
        actor_id, rol = _actor()
        return jsonify(representar_dispositivo(dispositivos().editar(actor_id=actor_id, rol=rol,
                                                           id_dispositivo=id_dispositivo, nombre=datos["nombre"])))
    return ejecutar(operacion, accion="EDITAR_DISPOSITIVO_EDGE", recurso_tipo="DISPOSITIVO_EDGE", recurso_id=id_dispositivo)


@bp.patch("/<int:id_dispositivo>/estado")
@requerir_roles(*TODOS)
def cambiar_estado_dispositivo(id_dispositivo: int):
    def operacion():
        sin_parametros()
        datos = cuerpo({"estado"}, obligatorios={"estado"})
        actor_id, rol = _actor()
        return jsonify(representar_dispositivo(dispositivos().cambiar_estado(actor_id=actor_id, rol=rol,
            id_dispositivo=id_dispositivo, estado=datos["estado"])))
    return ejecutar(operacion, accion="CAMBIAR_ESTADO_DISPOSITIVO", recurso_tipo="DISPOSITIVO_EDGE", recurso_id=id_dispositivo)


@bp.patch("/<int:id_dispositivo>/modo")
@requerir_roles(*TODOS)
def cambiar_modo_dispositivo(id_dispositivo: int):
    def operacion():
        sin_parametros()
        datos = cuerpo({"modo_operacion"}, obligatorios={"modo_operacion"})
        actor_id, rol = _actor()
        return jsonify(representar_dispositivo(dispositivos().cambiar_modo(actor_id=actor_id, rol=rol,
            id_dispositivo=id_dispositivo, modo=datos["modo_operacion"])))
    return ejecutar(operacion, accion="CAMBIAR_MODO_DISPOSITIVO", recurso_tipo="DISPOSITIVO_EDGE",
                   recurso_id=id_dispositivo, detalle_fallo=lambda motivo: _detalle_modo_fallido(id_dispositivo, motivo))
