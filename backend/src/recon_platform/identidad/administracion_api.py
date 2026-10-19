"""API administrativa IAM; las reglas y transacciones permanecen en casos de uso."""

import re
from collections.abc import Callable

from flask import Blueprint, Response, g, jsonify, request

from recon_platform.extensions import db
from recon_platform.identidad.api import _comprobar_host_local, requerir_roles
from recon_platform.identidad.aplicacion.casos_de_uso import (
    CambiarEstadoUsuario,
    CambiarRolUsuario,
    ConflictoIntegridadIAM,
    ConsultarUsuarioPlataforma,
    CrearUsuarioPlataforma,
    DatosInvalidosIAM,
    ListarRoles,
    ListarUsuariosPlataforma,
    PermisoDenegado,
    RolNoExiste,
    UsuarioDuplicado,
    UsuarioNoExiste,
)
from recon_platform.identidad.dominio.usuario_plataforma import UsuarioPlataforma
from recon_platform.identidad.infraestructura.repositorios import RepositorioIAMSQLAlchemy
from recon_platform.identidad.infraestructura.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy

bp = Blueprint("administracion_iam", __name__, url_prefix="/api/v1/iam")
bp.before_request(_comprobar_host_local)
ROLES_ASIGNABLES = frozenset({"ADMINISTRADOR", "OPERADOR"})
ESTADOS = frozenset({"ACTIVO", "INACTIVO"})


@bp.after_request
def _sin_cache(respuesta: Response) -> Response:
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


def _error(codigo: int, mensaje: str) -> tuple[Response, int]:
    return jsonify({"error": mensaje}), codigo


def _repositorio() -> tuple[RepositorioIAMSQLAlchemy, UnidadTrabajoIAMSQLAlchemy]:
    return RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session)


def _representar(usuario: UsuarioPlataforma) -> dict[str, int | str | None]:
    return {
        "id_usuario": usuario.id_usuario,
        "login": usuario.login,
        "rol": usuario.rol.nombre,
        "estado": usuario.estado,
    }


def _ejecutar(operacion: Callable[[], Response | tuple[Response, int]]) -> Response | tuple[Response, int]:
    try:
        return operacion()
    except UsuarioNoExiste:
        return _error(404, "La cuenta no existe.")
    except UsuarioDuplicado:
        return _error(409, "El identificador de login ya existe.")
    except PermisoDenegado:
        return _error(403, "Permiso denegado.")
    except (RolNoExiste, ConflictoIntegridadIAM):
        return _error(503, "La administración IAM no está disponible.")
    except DatosInvalidosIAM:
        return _error(400, "Los datos de la cuenta no son válidos.")
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return _error(503, "La administración IAM no está disponible.")


def _cuerpo_exacto(*campos: str) -> dict | None:
    cuerpo = request.get_json(silent=True)
    if not isinstance(cuerpo, dict) or set(cuerpo) != set(campos):
        return None
    return cuerpo


def _paginacion() -> tuple[int, int] | None:
    if set(request.args) - {"limite", "desplazamiento"}:
        return None
    if any(len(request.args.getlist(clave)) != 1 for clave in request.args):
        return None
    limite_texto = request.args.get("limite", "50")
    desplazamiento_texto = request.args.get("desplazamiento", "0")
    if not re.fullmatch(r"[0-9]{1,7}", limite_texto) or not re.fullmatch(
        r"[0-9]{1,7}", desplazamiento_texto
    ):
        return None
    limite, desplazamiento = int(limite_texto), int(desplazamiento_texto)
    if not 1 <= limite <= 100 or desplazamiento > 1_000_000:
        return None
    return limite, desplazamiento


@bp.get("/roles")
@requerir_roles("SUPERADMIN")
def listar_roles() -> Response | tuple[Response, int]:
    def operacion() -> Response:
        repositorio, unidad = _repositorio()
        roles = ListarRoles(repositorio, unidad).ejecutar(actor_id=g.identidad_iam.id_usuario)
        return jsonify({"roles": [
            {"nombre": rol.nombre, "asignable": rol.nombre in ROLES_ASIGNABLES}
            for rol in roles
        ]})

    return _ejecutar(operacion)


@bp.get("/usuarios")
@requerir_roles("SUPERADMIN")
def listar_usuarios() -> Response | tuple[Response, int]:
    paginacion = _paginacion()
    if paginacion is None:
        return _error(400, "La paginación no es válida.")
    limite, desplazamiento = paginacion

    def operacion() -> Response:
        repositorio, unidad = _repositorio()
        usuarios = ListarUsuariosPlataforma(repositorio, unidad).ejecutar(
            actor_id=g.identidad_iam.id_usuario,
            limite=limite, desplazamiento=desplazamiento,
        )
        return jsonify({
            "usuarios": [_representar(usuario) for usuario in usuarios],
            "limite": limite, "desplazamiento": desplazamiento,
        })

    return _ejecutar(operacion)


@bp.get("/usuarios/<int:usuario_id>")
@requerir_roles("SUPERADMIN")
def consultar_usuario(usuario_id: int) -> Response | tuple[Response, int]:
    def operacion() -> Response:
        repositorio, unidad = _repositorio()
        usuario = ConsultarUsuarioPlataforma(repositorio, unidad).ejecutar(
            actor_id=g.identidad_iam.id_usuario, usuario_id=usuario_id
        )
        return jsonify(_representar(usuario))

    return _ejecutar(operacion)


@bp.post("/usuarios")
@requerir_roles("SUPERADMIN")
def crear_usuario() -> Response | tuple[Response, int]:
    cuerpo = _cuerpo_exacto("login", "contrasena", "rol")
    if (cuerpo is None or not isinstance(cuerpo["login"], str)
        or not isinstance(cuerpo["contrasena"], str)
        or not isinstance(cuerpo["rol"], str)
        or cuerpo["rol"] not in ROLES_ASIGNABLES):
        return _error(400, "Los datos de la cuenta no son válidos.")

    def operacion() -> tuple[Response, int]:
        repositorio, unidad = _repositorio()
        usuario = CrearUsuarioPlataforma(repositorio, unidad).ejecutar(
            actor_id=g.identidad_iam.id_usuario,
            login=cuerpo["login"], contrasena=cuerpo["contrasena"],
            rol_nombre=cuerpo["rol"],
        )
        respuesta = jsonify(_representar(usuario))
        respuesta.headers["Location"] = f"/api/v1/iam/usuarios/{usuario.id_usuario}"
        return respuesta, 201

    return _ejecutar(operacion)


@bp.patch("/usuarios/<int:usuario_id>/rol")
@requerir_roles("SUPERADMIN")
def cambiar_rol(usuario_id: int) -> Response | tuple[Response, int]:
    cuerpo = _cuerpo_exacto("rol")
    if (cuerpo is None or not isinstance(cuerpo["rol"], str)
        or cuerpo["rol"] not in ROLES_ASIGNABLES):
        return _error(400, "El rol solicitado no es válido.")

    def operacion() -> Response:
        repositorio, unidad = _repositorio()
        usuario = CambiarRolUsuario(repositorio, unidad).ejecutar(
            actor_id=g.identidad_iam.id_usuario,
            usuario_id=usuario_id, rol_nombre=cuerpo["rol"],
        )
        return jsonify(_representar(usuario))

    return _ejecutar(operacion)


@bp.patch("/usuarios/<int:usuario_id>/estado")
@requerir_roles("SUPERADMIN")
def cambiar_estado(usuario_id: int) -> Response | tuple[Response, int]:
    cuerpo = _cuerpo_exacto("estado")
    if (cuerpo is None or not isinstance(cuerpo["estado"], str)
        or cuerpo["estado"] not in ESTADOS):
        return _error(400, "El estado solicitado no es válido.")

    def operacion() -> Response:
        repositorio, unidad = _repositorio()
        usuario = CambiarEstadoUsuario(repositorio, unidad).ejecutar(
            actor_id=g.identidad_iam.id_usuario,
            usuario_id=usuario_id, estado=cuerpo["estado"],
        )
        return jsonify(_representar(usuario))

    return _ejecutar(operacion)
