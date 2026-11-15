"""Representación administrativa explícita de PuntoAcceso."""

from recon_platform.accesos.dominio.punto_acceso import PuntoAcceso


def representar_punto(punto: PuntoAcceso) -> dict:
    return {"id_punto_acceso": punto.id_punto_acceso, "codigo": punto.codigo,
            "nombre": punto.nombre, "descripcion": punto.descripcion, "estado": punto.estado,
            "fecha_creacion": punto.fecha_creacion.isoformat() if punto.fecha_creacion else None,
            "fecha_actualizacion": punto.fecha_actualizacion.isoformat() if punto.fecha_actualizacion else None}
