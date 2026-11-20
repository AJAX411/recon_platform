"""Contrato administrativo de Personas; no incorpora reglas biométricas."""

from recon_platform.personas.persona import Persona
from recon_platform.personas.tipo_persona import TIPOS_PERSONA_INICIALES


def representar_persona(persona: Persona) -> dict:
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


CAMPOS = frozenset({"primer_nombre", "segundo_nombre", "primer_apellido",
                    "segundo_apellido", "tipo_documento", "numero_documento",
                    "identificador_institucional", "tipo_persona"})
OBLIGATORIOS = frozenset({"primer_nombre", "primer_apellido", "tipo_documento",
                          "numero_documento", "tipo_persona"})


def validar_cuerpo_persona(datos: object, *, nuevo: bool) -> dict | None:
    cuerpo = datos
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
