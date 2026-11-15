"""API HTTP administrativa de Personas; IAM valida sesión, rol y CSRF."""

import re
from collections.abc import Callable

from flask import Blueprint, Response, g, jsonify, request

from recon_platform.extensions import db
from recon_platform.identidad.controladores.seguridad import comprobar_transporte_web, requerir_roles
from recon_platform.personas.servicios.personas import (
    ActorPersonas,
    ConflictoIntegridad,
    DatosInvalidosPersona,
    PersonaDuplicada,
    PersonaNoExiste,
    PermisoPersonasDenegado,
    TipoPersonaNoExiste,
)
from recon_platform.personas.dominio.persona import Persona
from recon_platform.personas.dominio.tipo_persona import TIPOS_PERSONA_INICIALES, TipoPersona
from recon_platform.personas.dto.personas import representar_persona, validar_cuerpo_persona
from recon_platform.composicion import crear_administracion_personas

bp = Blueprint("administracion_personas", __name__, url_prefix="/api/v1/personas")

bp.before_request(comprobar_transporte_web)

ROLES = ("SUPERADMIN", "ADMINISTRADOR")
FILTROS = frozenset({"tipo_documento", "numero_documento",
                     "identificador_institucional", "tipo_persona", "estado"})


@bp.after_request
def _sin_cache(respuesta: Response) -> Response:
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


def _error(codigo: int, mensaje: str) -> tuple[Response, int]:
    return jsonify({"error": mensaje}), codigo


def _actor() -> ActorPersonas:
    return ActorPersonas(g.identidad_iam.id_usuario, g.identidad_iam.rol_nombre)


def _ejecutar(operacion: Callable):
    try:
        return operacion()
    except PersonaNoExiste:
        return _error(404, "La Persona no existe.")
    except PersonaDuplicada:
        return _error(409, "El identificador de Persona ya existe.")
    except PermisoPersonasDenegado:
        return _error(403, "Permiso denegado.")
    except TipoPersonaNoExiste:
        return _error(400, "El TipoPersona no está disponible.")
    except DatosInvalidosPersona:
        return _error(400, "Los datos de Persona no son válidos.")
    except ConflictoIntegridad:
        return _error(503, "La administración de Personas no está disponible.")
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return _error(503, "La administración de Personas no está disponible.")


def _cuerpo(*, nuevo: bool) -> dict | None:
    return validar_cuerpo_persona(request.get_json(silent=True), nuevo=nuevo)


def _paginacion_y_filtros() -> tuple[int, int, dict[str, str]] | None:
    if set(request.args) - FILTROS - {"limite", "desplazamiento"}:
        return None
    if any(len(request.args.getlist(clave)) != 1 for clave in request.args):
        return None
    limite_texto = request.args.get("limite", "50")
    desplazamiento_texto = request.args.get("desplazamiento", "0")
    if not re.fullmatch(r"[0-9]{1,7}", limite_texto) or not re.fullmatch(r"[0-9]{1,7}", desplazamiento_texto):
        return None
    limite, desplazamiento = int(limite_texto), int(desplazamiento_texto)
    if not 1 <= limite <= 100 or desplazamiento > 1_000_000:
        return None
    filtros = {nombre: request.args[nombre] for nombre in FILTROS if nombre in request.args}
    if any(not valor.strip() for valor in filtros.values()):
        return None
    if filtros.get("tipo_persona", "VISITANTE") not in TIPOS_PERSONA_INICIALES:
        return None
    if filtros.get("estado", "ACTIVO") not in {"ACTIVO", "INACTIVO"}:
        return None
    maximos = {"tipo_documento": 20, "numero_documento": 30,
               "identificador_institucional": 50, "tipo_persona": 50, "estado": 20}
    if any(len(valor) > maximos[nombre] for nombre, valor in filtros.items()):
        return None
    return limite, desplazamiento, filtros


@bp.get("/tipos")
@requerir_roles(*ROLES)
def listar_tipos():
    if request.args:
        return _error(400, "Los parámetros no son válidos.")
    return _ejecutar(lambda: jsonify({"tipos": [
        {"id_tipo_persona": tipo.id_tipo_persona, "nombre": tipo.nombre,
         "descripcion": tipo.descripcion, "estado": tipo.estado}
        for tipo in crear_administracion_personas().listar_tipos(actor=_actor())]}))


@bp.get("")
@requerir_roles(*ROLES)
def listar_personas():
    parametros = _paginacion_y_filtros()
    if parametros is None:
        return _error(400, "La paginación o los filtros no son válidos.")
    limite, desplazamiento, filtros = parametros
    return _ejecutar(lambda: jsonify({
        "personas": [representar_persona(persona) for persona in crear_administracion_personas().listar(
            actor=_actor(), limite=limite, desplazamiento=desplazamiento, filtros=filtros)],
        "limite": limite, "desplazamiento": desplazamiento,
    }))


@bp.get("/<int:id_persona>")
@requerir_roles(*ROLES)
def consultar_persona(id_persona: int):
    if id_persona <= 0 or request.args:
        return _error(400, "El identificador o los parámetros no son válidos.")
    return _ejecutar(lambda: jsonify(representar_persona(
        crear_administracion_personas().consultar(actor=_actor(), id_persona=id_persona))))


@bp.post("")
@requerir_roles(*ROLES)
def registrar_persona():
    if request.args:
        return _error(400, "Los parámetros no son válidos.")
    cuerpo = _cuerpo(nuevo=True)
    if cuerpo is None:
        return _error(400, "Los datos de Persona no son válidos.")
    try:
        persona = Persona(**{k: v for k, v in cuerpo.items() if k != "tipo_persona"},
                          tipo_persona=TipoPersona(nombre=cuerpo["tipo_persona"]))
    except ValueError:
        return _error(400, "Los datos de Persona no son válidos.")

    def operacion():
        guardada = crear_administracion_personas().registrar(actor=_actor(), persona=persona)
        respuesta = jsonify(representar_persona(guardada))
        respuesta.headers["Location"] = f"/api/v1/personas/{guardada.id_persona}"
        return respuesta, 201
    return _ejecutar(operacion)


@bp.patch("/<int:id_persona>")
@requerir_roles(*ROLES)
def actualizar_persona(id_persona: int):
    if id_persona <= 0 or request.args:
        return _error(400, "El identificador o los parámetros no son válidos.")
    cuerpo = _cuerpo(nuevo=False)
    if cuerpo is None:
        return _error(400, "Los datos de Persona no son válidos.")
    return _ejecutar(lambda: jsonify(representar_persona(crear_administracion_personas().actualizar(
        actor=_actor(), id_persona=id_persona, datos=cuerpo))))


@bp.patch("/<int:id_persona>/estado")
@requerir_roles(*ROLES)
def cambiar_estado_persona(id_persona: int):
    if id_persona <= 0 or request.args:
        return _error(400, "El identificador o los parámetros no son válidos.")
    cuerpo = request.get_json(silent=True)
    if not isinstance(cuerpo, dict) or set(cuerpo) != {"estado"} or cuerpo["estado"] not in ("ACTIVO", "INACTIVO"):
        return _error(400, "El estado solicitado no es válido.")
    return _ejecutar(lambda: jsonify(representar_persona(crear_administracion_personas().cambiar_estado(
        actor=_actor(), id_persona=id_persona, estado=cuerpo["estado"]))))
