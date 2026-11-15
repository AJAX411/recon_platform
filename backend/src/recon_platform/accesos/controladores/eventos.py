"""API web humana de EventoAcceso; no expone una frontera Edge."""

from datetime import UTC, datetime

from flask import Blueprint, Response, g, jsonify, request

from recon_platform.accesos.servicios.eventos import (
    ActorAcceso,
    ConflictoIdempotencia,
    ReferenciaNoDisponible,
)
from recon_platform.accesos.dominio.evento_acceso import INCIDENCIAS, MOVIMIENTOS, RESULTADOS
from recon_platform.composicion import auditoria
from recon_platform.extensions import db
from recon_platform.http.administrativo import paginacion, registrar_denegacion, sin_parametros
from recon_platform.identidad.controladores.seguridad import comprobar_transporte_web, requerir_roles
from recon_platform.accesos.dto.eventos import representar_evento_manual, validar_cuerpo_manual
from recon_platform.composicion import crear_consulta_eventos
from recon_platform.composicion import crear_registro_manual

bp = Blueprint("eventos_acceso", __name__, url_prefix="/api/v1/eventos-acceso")

bp.before_request(comprobar_transporte_web)

TODOS = ("OPERADOR", "ADMINISTRADOR", "SUPERADMIN")
ADMIN = ("ADMINISTRADOR", "SUPERADMIN")
FILTROS = {"id_persona", "id_punto_acceso", "tipo_movimiento", "resultado",
           "tipo_incidencia_secuencia", "desde", "hasta"}


def _reloj() -> datetime:
    return datetime.now(UTC)


@bp.after_request
def _sin_cache(respuesta: Response) -> Response:
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


def _error(codigo: int, mensaje: str):
    return jsonify({"error": mensaje}), codigo


def _actor() -> ActorAcceso:
    identidad = g.identidad_iam
    return ActorAcceso(identidad.id_usuario, identidad.rol_nombre)


def _auditar_fallo(motivo: str) -> bool:
    try:
        db.session.rollback()
        auditoria().registrar_fallo(actor_id=g.identidad_iam.id_usuario,
            accion="REGISTRAR_EVENTO_ACCESO_MANUAL", recurso_tipo="EVENTO_ACCESO",
            detalle=motivo)
        return True
    except Exception:
        db.session.rollback()
        return False


def _ejecutar(operacion, *, escritura: bool = False):
    try:
        return operacion()
    except ReferenciaNoDisponible:
        codigo, motivo, mensaje = 404, "REFERENCIA_NO_DISPONIBLE", "Referencia no disponible."
    except ConflictoIdempotencia:
        codigo, motivo, mensaje = 409, "CLAVE_REUTILIZADA", "La clave ya corresponde a otra declaración."
    except PermissionError:
        codigo, motivo, mensaje = 403, "PERMISO_DENEGADO", "Permiso denegado."
    except ValueError:
        codigo, motivo, mensaje = 400, "DATOS_INVALIDOS", "Los datos no son válidos."
    except Exception:
        db.session.rollback()
        return _error(503, "El registro de accesos no está disponible.")
    db.session.rollback()
    if escritura and not _auditar_fallo(motivo):
        return _error(503, "La auditoría no está disponible.")
    return _error(codigo, mensaje)


def _filtros() -> tuple[int, int, dict[str, str | int | datetime]]:
    limite, desplazamiento, filtros_texto = paginacion(FILTROS)
    filtros: dict[str, str | int | datetime] = dict(filtros_texto)
    fechas: dict[str, datetime] = {}
    for campo in ("id_persona", "id_punto_acceso"):
        if campo in filtros_texto:
            valor = filtros_texto[campo]
            if not valor.isdecimal() or len(valor) > 10 or int(valor) <= 0:
                raise ValueError("Identificador inválido.")
            filtros[campo] = int(valor)
    enumerados = {"tipo_movimiento": MOVIMIENTOS, "resultado": RESULTADOS,
                  "tipo_incidencia_secuencia": INCIDENCIAS}
    for campo, permitidos in enumerados.items():
        if campo in filtros_texto and filtros_texto[campo] not in permitidos:
            raise ValueError("Filtro inválido.")
    for campo in ("desde", "hasta"):
        if campo in filtros_texto:
            try:
                fecha = datetime.fromisoformat(filtros_texto[campo])
            except ValueError as error:
                raise ValueError("Fecha inválida.") from error
            if fecha.tzinfo is None:
                raise ValueError("Fecha sin zona.")
            fecha_utc = fecha.astimezone(UTC)
            filtros[campo] = fecha_utc
            fechas[campo] = fecha_utc
    if "desde" in fechas and "hasta" in fechas and fechas["desde"] >= fechas["hasta"]:
        raise ValueError("Rango inválido.")
    return limite, desplazamiento, filtros


@bp.get("/personas-elegibles")
@requerir_roles(*TODOS)
def personas_elegibles():
    def operacion():
        if set(request.args) != {"criterio", "valor"} or any(
            len(request.args.getlist(clave)) != 1 for clave in request.args
        ):
            raise ValueError("Búsqueda inválida.")
        personas = crear_consulta_eventos(_reloj).buscar_personas(actor=_actor(),
            criterio=request.args["criterio"], valor=request.args["valor"])
        return jsonify({"personas": personas})
    return _ejecutar(operacion)


@bp.post("/manual")
@requerir_roles(*TODOS)
def registrar_manual():
    def operacion():
        sin_parametros()
        datos = validar_cuerpo_manual(request.get_json(silent=True))
        clave = request.headers.get("Idempotency-Key")
        registro = crear_registro_manual(_reloj).ejecutar(actor=_actor(),
            id_persona=datos["id_persona"], id_punto_acceso=datos["id_punto_acceso"],
            tipo_movimiento=datos["tipo_movimiento"],
            clave=clave)
        e = registro.evento
        respuesta = jsonify(representar_evento_manual(e))
        respuesta.headers["Idempotent-Replay"] = "true" if registro.repetido else "false"
        return respuesta, 200 if registro.repetido else 201
    return _ejecutar(operacion, escritura=True)


@bp.get("/historial")
@requerir_roles(*TODOS)
def historial():
    def operacion():
        limite, desplazamiento, filtros = _filtros()
        filas = crear_consulta_eventos(_reloj).historial(actor=_actor(), limite=limite,
            desplazamiento=desplazamiento, filtros=filtros)
        return jsonify({"eventos": filas, "limite": limite, "desplazamiento": desplazamiento,
                        "alcance": "JORNADA_ACTUAL_REDUCIDA" if _actor().rol == "OPERADOR"
                                   else "HISTORICO_AMPLIADO"})
    return _ejecutar(operacion)


@bp.get("/alertas")
@requerir_roles(*TODOS)
def alertas():
    def operacion():
        limite, desplazamiento, filtros = _filtros()
        proyeccion = crear_consulta_eventos(_reloj).alertas(actor=_actor(), limite=limite,
            desplazamiento=desplazamiento, filtros=filtros)
        if isinstance(proyeccion, dict):
            return jsonify({"conteos_por_incidencia": proyeccion, "zona_horaria": "America/Bogota"})
        return jsonify({"alertas": proyeccion, "limite": limite,
                        "desplazamiento": desplazamiento})
    return _ejecutar(operacion)


@bp.get("/incidencias/<int:id_evento>")
@requerir_roles(*ADMIN, al_denegar=lambda identidad, id_evento:
    registrar_denegacion(identidad, accion="CONSULTAR_INCIDENCIA_ACCESO",
                        recurso_tipo="EVENTO_ACCESO"))
def detalle_incidencia(id_evento: int):
    def operacion():
        sin_parametros()
        return jsonify(crear_consulta_eventos(_reloj).detalle(actor=_actor(), id_evento=id_evento))
    return _ejecutar(operacion)
