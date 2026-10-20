"""API HTTP administrativa de Personas; IAM valida sesión, rol y CSRF."""

import re
from collections.abc import Callable

from flask import Blueprint, Response, g, jsonify, request

from recon_platform.extensions import db
from recon_platform.identidad.api import _comprobar_host_local, requerir_roles
from recon_platform.personas.aplicacion.casos_de_uso import (
    ActorPersonas, AdministrarPersonas, ConflictoIntegridad, DatosInvalidosPersona, PersonaDuplicada,
    PersonaNoExiste, PermisoPersonasDenegado, TipoPersonaNoExiste,
)
from recon_platform.personas.dominio.persona import Persona
from recon_platform.personas.dominio.tipo_persona import TIPOS_PERSONA_INICIALES, TipoPersona
from recon_platform.personas.infraestructura.repositorios import (
    RepositorioPersonasSQLAlchemy, RepositorioTiposPersonaSQLAlchemy,
)
from recon_platform.personas.infraestructura.unidad_trabajo import UnidadTrabajoSQLAlchemy

bp = Blueprint("administracion_personas", __name__, url_prefix="/api/v1/personas")
bp.before_request(_comprobar_host_local)
ROLES = ("SUPERADMIN", "ADMINISTRADOR")
CAMPOS = frozenset({"primer_nombre", "segundo_nombre", "primer_apellido",
                    "segundo_apellido", "tipo_documento", "numero_documento",
                    "identificador_institucional", "tipo_persona"})
OBLIGATORIOS = frozenset({"primer_nombre", "primer_apellido", "tipo_documento",
                          "numero_documento", "tipo_persona"})
FILTROS = frozenset({"tipo_documento", "numero_documento",
                     "identificador_institucional", "tipo_persona", "estado"})


@bp.after_request
def _sin_cache(respuesta: Response) -> Response:
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


def _error(codigo: int, mensaje: str) -> tuple[Response, int]:
    return jsonify({"error": mensaje}), codigo


def _caso() -> AdministrarPersonas:
    return AdministrarPersonas(RepositorioPersonasSQLAlchemy(db.session),
                              RepositorioTiposPersonaSQLAlchemy(db.session),
                              UnidadTrabajoSQLAlchemy(db.session))


def _actor() -> ActorPersonas:
    return ActorPersonas(g.identidad_iam.id_usuario, g.identidad_iam.rol_nombre)


def _representar(persona: Persona) -> dict:
    return {
        "id_persona": persona.id_persona,
        "primer_nombre": persona.primer_nombre,
        "segundo_nombre": persona.segundo_nombre,
        "primer_apellido": persona.primer_apellido,
        "segundo_apellido": persona.segundo_apellido,
        "tipo_documento": persona.tipo_documento,
        "numero_documento": persona.numero_documento,
        "identificador_institucional": persona.identificador_institucional,
        "tipo_persona": persona.tipo_persona.nombre,
        "estado": persona.estado,
        "fecha_creacion": persona.fecha_creacion.isoformat() if persona.fecha_creacion else None,
        "fecha_actualizacion": persona.fecha_actualizacion.isoformat() if persona.fecha_actualizacion else None,
    }


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
    cuerpo = request.get_json(silent=True)
    if not isinstance(cuerpo, dict) or not set(cuerpo) <= CAMPOS:
        return None
    if nuevo and not OBLIGATORIOS <= set(cuerpo):
        return None
    if not nuevo and not cuerpo:
        return None
    for nombre, valor in cuerpo.items():
        if nombre in {"segundo_nombre", "segundo_apellido", "identificador_institucional"} and valor is None:
            continue
        if not isinstance(valor, str):
            return None
        if nombre == "tipo_persona" and valor not in TIPOS_PERSONA_INICIALES:
            return None
    return cuerpo


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
        for tipo in _caso().listar_tipos(actor=_actor())]}))


@bp.get("")
@requerir_roles(*ROLES)
def listar_personas():
    parametros = _paginacion_y_filtros()
    if parametros is None:
        return _error(400, "La paginación o los filtros no son válidos.")
    limite, desplazamiento, filtros = parametros
    return _ejecutar(lambda: jsonify({
        "personas": [_representar(persona) for persona in _caso().listar(
            actor=_actor(), limite=limite, desplazamiento=desplazamiento, filtros=filtros)],
        "limite": limite, "desplazamiento": desplazamiento,
    }))


@bp.get("/<int:id_persona>")
@requerir_roles(*ROLES)
def consultar_persona(id_persona: int):
    if id_persona <= 0 or request.args:
        return _error(400, "El identificador o los parámetros no son válidos.")
    return _ejecutar(lambda: jsonify(_representar(
        _caso().consultar(actor=_actor(), id_persona=id_persona))))


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
        guardada = _caso().registrar(actor=_actor(), persona=persona)
        respuesta = jsonify(_representar(guardada))
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
    return _ejecutar(lambda: jsonify(_representar(_caso().actualizar(
        actor=_actor(), id_persona=id_persona, datos=cuerpo))))


@bp.patch("/<int:id_persona>/estado")
@requerir_roles(*ROLES)
def cambiar_estado_persona(id_persona: int):
    if id_persona <= 0 or request.args:
        return _error(400, "El identificador o los parámetros no son válidos.")
    cuerpo = request.get_json(silent=True)
    if not isinstance(cuerpo, dict) or set(cuerpo) != {"estado"} or cuerpo["estado"] not in ("ACTIVO", "INACTIVO"):
        return _error(400, "El estado solicitado no es válido.")
    return _ejecutar(lambda: jsonify(_representar(_caso().cambiar_estado(
        actor=_actor(), id_persona=id_persona, estado=cuerpo["estado"]))))
