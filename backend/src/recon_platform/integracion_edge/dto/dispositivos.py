"""Representación administrativa; no informa conectividad física."""

from recon_platform.integracion_edge.dominio.dispositivo_edge import DispositivoEdge


def representar_dispositivo(d: DispositivoEdge) -> dict:
    return {"id_dispositivo": d.id_dispositivo, "id_punto_acceso": d.id_punto_acceso,
            "codigo": d.codigo, "nombre": d.nombre, "modo_operacion": d.modo_operacion,
            "estado": d.estado,
            "ultima_comunicacion": d.ultima_comunicacion.isoformat() if d.ultima_comunicacion else None,
            "fecha_creacion": d.fecha_creacion.isoformat() if d.fecha_creacion else None,
            "fecha_actualizacion": d.fecha_actualizacion.isoformat() if d.fecha_actualizacion else None}
