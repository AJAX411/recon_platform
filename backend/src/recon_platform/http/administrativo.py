"""Validación HTTP común de las nuevas APIs administrativas."""

import re
from collections.abc import Callable

from flask import Response, g, jsonify, request

from recon_platform.accesos.servicios.puntos import (
    IntegridadPunto,
    PermisoPuntoDenegado,
    PuntoDuplicado,
    PuntoNoExiste,
)
from recon_platform.composicion import auditoria
from recon_platform.extensions import db
from recon_platform.integracion_edge.servicios.dispositivos import (
    DispositivoDuplicado,
    DispositivoNoExiste,
    IntegridadDispositivo,
    PermisoDispositivoDenegado,
    PuntoAsociadoNoExiste,
)


def error(codigo: int, mensaje: str) -> tuple[Response, int]:
    return jsonify({"error": mensaje}), codigo


def cuerpo(campos: set[str], *, obligatorios: set[str] | None = None) -> dict:
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict) or not datos or not set(datos) <= campos:
        raise ValueError("Cuerpo inválido.")
    if obligatorios is not None and not obligatorios <= set(datos):
        raise ValueError("Campos obligatorios ausentes.")
    return datos


def paginacion(campos_filtro: set[str]) -> tuple[int, int, dict[str, str]]:
    if set(request.args) - campos_filtro - {"limite", "desplazamiento"}:
        raise ValueError("Parámetros desconocidos.")
    if any(len(request.args.getlist(clave)) != 1 for clave in request.args):
        raise ValueError("Parámetros repetidos.")
    limite = request.args.get("limite", "50")
    desplazamiento = request.args.get("desplazamiento", "0")
    if not re.fullmatch(r"[0-9]{1,7}", limite) or not re.fullmatch(r"[0-9]{1,7}", desplazamiento):
        raise ValueError("Paginación inválida.")
    n_limite, n_desplazamiento = int(limite), int(desplazamiento)
    if not 1 <= n_limite <= 100 or n_desplazamiento > 1_000_000:
        raise ValueError("Paginación inválida.")
    return n_limite, n_desplazamiento, {k: request.args[k] for k in campos_filtro if k in request.args}


def sin_parametros() -> None:
    if request.args:
        raise ValueError("Parámetros no admitidos.")


def registrar_denegacion(identidad, *, accion: str, recurso_tipo: str,
                         recurso_id: int | None = None, detalle: str = "PERMISO_DENEGADO") -> None:
    db.session.rollback()
    auditoria().registrar_fallo(actor_id=identidad.id_usuario, accion=accion,
                                recurso_tipo=recurso_tipo, recurso_id=recurso_id,
                                detalle=detalle)


def ejecutar(operacion: Callable, *, accion: str | None = None,
            recurso_tipo: str | None = None, recurso_id: int | None = None,
            detalle_fallo: Callable[[str], str] | None = None):
    try:
        return operacion()
    except (PuntoNoExiste, DispositivoNoExiste):
        codigo, motivo = 404, "RECURSO_NO_EXISTE"
    except PuntoAsociadoNoExiste:
        codigo, motivo = 400, "PUNTO_ASOCIADO_NO_EXISTE"
    except (PuntoDuplicado, DispositivoDuplicado):
        codigo, motivo = 409, "CODIGO_DUPLICADO"
    except (IntegridadPunto, IntegridadDispositivo):
        db.session.rollback()
        return error(503, "La administración no está disponible.")
    except (PermissionError, PermisoPuntoDenegado, PermisoDispositivoDenegado):
        codigo, motivo = 403, "PERMISO_DENEGADO"
    except ValueError:
        codigo, motivo = 400, "DATOS_INVALIDOS"
    except Exception:
        db.session.rollback()
        return error(503, "La administración no está disponible.")
    db.session.rollback()
    if accion is not None and recurso_tipo is not None:
        try:
            detalle = detalle_fallo(motivo) if detalle_fallo is not None else motivo
            auditoria().registrar_fallo(actor_id=g.identidad_iam.id_usuario,
                accion=accion, recurso_tipo=recurso_tipo, recurso_id=recurso_id,
                detalle=detalle)
        except Exception:
            db.session.rollback()
            return error(503, "La auditoría no está disponible.")
    if codigo == 404:
        return error(codigo, "El recurso no existe.")
    if codigo == 409:
        return error(codigo, "El código ya existe.")
    if codigo == 403:
        return error(codigo, "Permiso denegado.")
    return error(codigo, "Los datos no son válidos.")
