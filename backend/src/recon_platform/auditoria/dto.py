"""Representación de auditoría general con selección explícita de campos."""

from recon_platform.auditoria.evento_auditoria import EventoAuditoria


def representar_auditoria(e: EventoAuditoria) -> dict:
    fecha_hora = e.fecha_hora
    if fecha_hora is None:
        raise AttributeError("'NoneType' object has no attribute 'isoformat'")
    return {"id_auditoria": e.id_auditoria, "id_usuario_actor": e.id_usuario_actor,
            "tipo_actor": e.tipo_actor, "accion": e.accion, "recurso_tipo": e.recurso_tipo,
            "id_recurso_afectado": e.id_recurso_afectado, "resultado": e.resultado,
            "detalle": e.detalle, "fecha_hora": fecha_hora.isoformat()}
