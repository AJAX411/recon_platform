"""Clasificación principal de personas del prototipo."""

from dataclasses import dataclass

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
ESTADOS_TIPO_PERSONA = frozenset({"ACTIVO", "INACTIVO"})


@dataclass(kw_only=True, slots=True)
class TipoPersona:
    """Catálogo controlado, separado de las cuentas de plataforma."""

    nombre: str
    descripcion: str | None = None
    estado: str = "ACTIVO"
    id_tipo_persona: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.nombre, str) or self.nombre not in TIPOS_PERSONA_INICIALES:
            raise ValueError("El tipo de persona no pertenece al catálogo permitido.")
        if self.descripcion is not None:
            if not isinstance(self.descripcion, str) or not self.descripcion.strip():
                raise ValueError("La descripción debe contener texto no vacío.")
            self.descripcion = self.descripcion.strip()
            if len(self.descripcion) > 200:
                raise ValueError("La descripción supera 200 caracteres.")
        if not isinstance(self.estado, str) or self.estado not in ESTADOS_TIPO_PERSONA:
            raise ValueError("El estado de TipoPersona debe ser ACTIVO o INACTIVO.")
        if self.id_tipo_persona is not None and (
            not isinstance(self.id_tipo_persona, int) or self.id_tipo_persona <= 0
        ):
            raise ValueError("id_tipo_persona debe ser un entero positivo.")
