"""Contrato MANUAL; las proyecciones por rol conservan su adaptador actual."""

from recon_platform.accesos.evento_acceso import EventoAcceso


def representar_evento_manual(e: EventoAcceso) -> dict:
    return {"id_evento_acceso": e.id_evento_acceso,
        "id_persona": e.id_persona, "id_punto_acceso": e.id_punto_acceso,
        "tipo_movimiento": e.tipo_movimiento, "resultado": e.resultado,
        "metodo_registro": e.metodo_registro,
        "id_usuario_registrador": e.id_usuario_registrador,
        "fecha_hora_ocurrencia": e.fecha_hora_ocurrencia.isoformat(),
        "tipo_incidencia_secuencia": e.tipo_incidencia_secuencia,
        "id_dispositivo": e.id_dispositivo}


def validar_cuerpo_manual(datos: object) -> dict:
    if (not isinstance(datos, dict)
        or set(datos) != {"id_persona", "id_punto_acceso", "tipo_movimiento"}):
        raise ValueError("Cuerpo inválido.")
    return datos
