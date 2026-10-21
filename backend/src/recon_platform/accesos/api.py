"""API administrativa de PuntoAcceso."""

from flask import Blueprint, Response, g, jsonify

from recon_platform.accesos.dominio import PuntoAcceso
from recon_platform.composicion_administrativa import puntos
from recon_platform.http_administrativo import cuerpo, ejecutar, paginacion, registrar_denegacion, sin_parametros
from recon_platform.identidad.api import _comprobar_host_local, requerir_roles

bp = Blueprint("puntos_acceso", __name__, url_prefix="/api/v1/puntos-acceso")
bp.before_request(_comprobar_host_local)
TODOS = ("SUPERADMIN", "ADMINISTRADOR", "OPERADOR")
ADMIN = ("SUPERADMIN", "ADMINISTRADOR")


@bp.after_request
def _sin_cache(respuesta: Response) -> Response:
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


def _actor() -> tuple[int, str]:
    return g.identidad_iam.id_usuario, g.identidad_iam.rol_nombre


def _representar(punto: PuntoAcceso) -> dict:
    return {"id_punto_acceso": punto.id_punto_acceso, "codigo": punto.codigo,
            "nombre": punto.nombre, "descripcion": punto.descripcion, "estado": punto.estado,
            "fecha_creacion": punto.fecha_creacion.isoformat() if punto.fecha_creacion else None,
            "fecha_actualizacion": punto.fecha_actualizacion.isoformat() if punto.fecha_actualizacion else None}


def _denegacion(accion: str):
    def registrar(identidad, id_punto: int | None = None):
        registrar_denegacion(identidad, accion=accion, recurso_tipo="PUNTO_ACCESO", recurso_id=id_punto)
    return registrar


@bp.get("")
@requerir_roles(*TODOS)
def listar_puntos():
    def operacion():
        limite, desplazamiento, filtros = paginacion({"codigo", "estado"})
        actor_id, rol = _actor()
        lista = puntos().listar(actor_id=actor_id, rol=rol, limite=limite,
                                desplazamiento=desplazamiento, filtros=filtros)
        return jsonify({"puntos": [_representar(p) for p in lista],
                        "limite": limite, "desplazamiento": desplazamiento})
    return ejecutar(operacion)


@bp.get("/<int:id_punto>")
@requerir_roles(*TODOS)
def consultar_punto(id_punto: int):
    def operacion():
        sin_parametros()
        actor_id, rol = _actor()
        return jsonify(_representar(puntos().consultar(actor_id=actor_id, rol=rol, id_punto=id_punto)))
    return ejecutar(operacion)


@bp.post("")
@requerir_roles(*ADMIN, al_denegar=_denegacion("CREAR_PUNTO_ACCESO"))
def crear_punto():
    def operacion():
        sin_parametros()
        datos = cuerpo({"codigo", "nombre", "descripcion"}, obligatorios={"codigo", "nombre"})
        actor_id, rol = _actor()
        guardado = puntos().crear(actor_id=actor_id, rol=rol, punto=PuntoAcceso(**datos))
        respuesta = jsonify(_representar(guardado))
        respuesta.headers["Location"] = f"/api/v1/puntos-acceso/{guardado.id_punto_acceso}"
        return respuesta, 201
    return ejecutar(operacion, accion="CREAR_PUNTO_ACCESO", recurso_tipo="PUNTO_ACCESO")


@bp.patch("/<int:id_punto>")
@requerir_roles(*ADMIN, al_denegar=_denegacion("EDITAR_PUNTO_ACCESO"))
def editar_punto(id_punto: int):
    def operacion():
        sin_parametros()
        datos = cuerpo({"nombre", "descripcion"})
        actor_id, rol = _actor()
        return jsonify(_representar(puntos().editar(actor_id=actor_id, rol=rol,
                                                    id_punto=id_punto, datos=datos)))
    return ejecutar(operacion, accion="EDITAR_PUNTO_ACCESO", recurso_tipo="PUNTO_ACCESO", recurso_id=id_punto)


@bp.patch("/<int:id_punto>/estado")
@requerir_roles(*TODOS)
def cambiar_estado_punto(id_punto: int):
    def operacion():
        sin_parametros()
        datos = cuerpo({"estado"}, obligatorios={"estado"})
        actor_id, rol = _actor()
        return jsonify(_representar(puntos().cambiar_estado(actor_id=actor_id, rol=rol,
                                                             id_punto=id_punto, estado=datos["estado"])))
    return ejecutar(operacion, accion="CAMBIAR_ESTADO_PUNTO", recurso_tipo="PUNTO_ACCESO", recurso_id=id_punto)
