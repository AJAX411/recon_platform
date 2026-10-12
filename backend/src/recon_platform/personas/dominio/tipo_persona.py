"""Clasificación institucional de las personas.

El catálogo corresponde a la propuesta provisional
del Contexto Maestro v1.5.
"""

from dataclasses import dataclass


# Clasificaciones iniciales del prototipo.
TIPOS_PERSONA_INICIALES = frozenset(
    {
        "ESTUDIANTE",
        "DOCENTE",
        "ADMINISTRATIVO",
        "SERVICIOS_GENERALES",
        "VISITANTE",
        "PERSONAL_SEGURIDAD",
    }
)

# Estados administrativos inicialmente permitidos.
ESTADOS_TIPO_PERSONA = frozenset(
    {
        "ACTIVO",
        "INACTIVO",
    }
)


@dataclass(kw_only=True, slots=True)
class TipoPersona:
    """Representa una clasificación institucional."""

    nombre: str
    descripcion: str | None = None
    estado: str = "ACTIVO"

    def __post_init__(self) -> None:
        """Valida los datos iniciales de TipoPersona."""

        # Validar la clasificación institucional.
        if (
            not isinstance(self.nombre, str)
            or self.nombre not in TIPOS_PERSONA_INICIALES
        ):
            raise ValueError(
                "El tipo de persona no pertenece al catálogo permitido."
            )

        # Validar la descripción cuando se proporciona.
        if self.descripcion is not None:
            if (
                not isinstance(self.descripcion, str)
                or not self.descripcion.strip()
            ):
                raise ValueError(
                    "La descripción debe contener texto no vacío."
                )

        # Validar el estado administrativo.
        if (
            not isinstance(self.estado, str)
            or self.estado not in ESTADOS_TIPO_PERSONA
        ):
            raise ValueError(
                "El estado de TipoPersona debe ser ACTIVO o INACTIVO."
            )
