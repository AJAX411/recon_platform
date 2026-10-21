"""API web administrativa de DispositivoEdge; no es contrato de la Raspberry."""

import json

from flask import Blueprint, Response, g, jsonify, request

from recon_platform.composicion_administrativa import dispositivos
from recon_platform.http_administrativo import cuerpo, ejecutar, paginacion, registrar_denegacion, sin_parametros
from recon_platform.identidad.api import _comprobar_host_local, requerir_roles
from recon_platform.integracion_edge.dominio import DispositivoEdge, MODOS

bp = Blueprint("dispositivos_edge", __name__, url_prefix="/api/v1/dispositivos-edge")
bp.before_request(_comprobar_host_local)
TODOS = ("SUPERADMIN", "ADMINISTRADOR", "OPERADOR")
ADMIN = ("SUPERADMIN", "ADMINISTRADOR")


@bp.after_request
def _sin_cache(respuesta: Response) -> Response:
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


def _actor() -> tuple[int, str]:
    return g.identidad_iam.id_usuario, g.identidad_iam.rol_nombre


def _representar(d: DispositivoEdge) -> dict:
    return {"id_dispositivo": d.id_dispositivo, "id_punto_acceso": d.id_punto_acceso,
            "codigo": d.codigo, "nombre": d.nombre, "modo_operacion": d.modo_operacion,
            "estado": d.estado,
            "ultima_comunicacion": d.ultima_comunicacion.isoformat() if d.ultima_comunicacion else None,
            "fecha_creacion": d.fecha_creacion.isoformat() if d.fecha_creacion else None,
            "fecha_actualizacion": d.fecha_actualizacion.isoformat() if d.fecha_actualizacion else None}


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
        limite, desplazamiento, filtros = paginacion({"codigo", "estado", "modo_operacion", "id_punto_acceso"})
        if "id_punto_acceso" in filtros:
            valor = filtros["id_punto_acceso"]
            if not valor.isdecimal() or len(valor) > 10:
                raise ValueError("Punto inválido.")
            filtros["id_punto_acceso"] = int(valor)
        actor_id, rol = _actor()
        lista = dispositivos().listar(actor_id=actor_id, rol=rol, limite=limite,
                                      desplazamiento=desplazamiento, filtros=filtros)
        return jsonify({"dispositivos": [_representar(d) for d in lista],
                        "limite": limite, "desplazamiento": desplazamiento})
    return ejecutar(operacion)


@bp.get("/<int:id_dispositivo>")
@requerir_roles(*TODOS)
def consultar_dispositivo(id_dispositivo: int):
    def operacion():
        sin_parametros()
        actor_id, rol = _actor()
        return jsonify(_representar(dispositivos().consultar(actor_id=actor_id, rol=rol,
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
        respuesta = jsonify(_representar(guardado))
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
        return jsonify(_representar(dispositivos().editar(actor_id=actor_id, rol=rol,
                                                           id_dispositivo=id_dispositivo, nombre=datos["nombre"])))
    return ejecutar(operacion, accion="EDITAR_DISPOSITIVO_EDGE", recurso_tipo="DISPOSITIVO_EDGE", recurso_id=id_dispositivo)


@bp.patch("/<int:id_dispositivo>/estado")
@requerir_roles(*TODOS)
def cambiar_estado_dispositivo(id_dispositivo: int):
    def operacion():
        sin_parametros()
        datos = cuerpo({"estado"}, obligatorios={"estado"})
        actor_id, rol = _actor()
        return jsonify(_representar(dispositivos().cambiar_estado(actor_id=actor_id, rol=rol,
            id_dispositivo=id_dispositivo, estado=datos["estado"])))
    return ejecutar(operacion, accion="CAMBIAR_ESTADO_DISPOSITIVO", recurso_tipo="DISPOSITIVO_EDGE", recurso_id=id_dispositivo)


@bp.patch("/<int:id_dispositivo>/modo")
@requerir_roles(*TODOS)
def cambiar_modo_dispositivo(id_dispositivo: int):
    def operacion():
        sin_parametros()
        datos = cuerpo({"modo_operacion"}, obligatorios={"modo_operacion"})
        actor_id, rol = _actor()
        return jsonify(_representar(dispositivos().cambiar_modo(actor_id=actor_id, rol=rol,
            id_dispositivo=id_dispositivo, modo=datos["modo_operacion"])))
    return ejecutar(operacion, accion="CAMBIAR_MODO_DISPOSITIVO", recurso_tipo="DISPOSITIVO_EDGE",
                   recurso_id=id_dispositivo, detalle_fallo=lambda motivo: _detalle_modo_fallido(id_dispositivo, motivo))
