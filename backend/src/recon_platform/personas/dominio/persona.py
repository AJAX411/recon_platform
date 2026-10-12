"""Representación inicial de una Persona en el dominio.

Esta versión incorpora nombres, apellidos e identificadores,
con validaciones básicas de los datos recibidos.

El esquema físico de MySQL y las relaciones definitivas
se definirán en etapas posteriores.
"""

from dataclasses import dataclass

from recon_platform.personas.dominio.tipo_persona import TipoPersona

ESTADOS_PERSONA = frozenset({"ACTIVO", "INACTIVO"})


@dataclass(kw_only=True, slots=True)
class Persona:
    """Representa los datos iniciales de identificación de una persona."""

    # Datos personales obligatorios.
    primer_nombre: str
    primer_apellido: str
    tipo_persona: TipoPersona
    estado: str = "ACTIVO"

    # Datos personales opcionales.
    segundo_nombre: str | None = None
    segundo_apellido: str | None = None

    # Identificador asignado por la institución.
    identificador_institucional: str | None = None

    # Documento de identidad.
    tipo_documento: str | None = None
    numero_documento: str | None = None

    def __post_init__(self) -> None:
        """Valida la clasificación, el estado y los datos de Persona."""

        if not isinstance(self.tipo_persona, TipoPersona):
            raise ValueError("La Persona debe tener un TipoPersona válido.")

        # Validar el estado administrativo de la Persona.
        if not isinstance(self.estado, str) or self.estado not in ESTADOS_PERSONA:
            raise ValueError("El estado de Persona debe ser ACTIVO o INACTIVO.")

        # El primer nombre y el primer apellido son obligatorios.
        campos_obligatorios = (
            "primer_nombre",
            "primer_apellido",
        )

        for campo in campos_obligatorios:
            valor = getattr(self, campo)

            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(
                    f"El campo '{campo}' es obligatorio y no puede estar vacío."
                )

        # Los identificadores son opcionales, pero deben ser válidos
        # cuando se proporciona un valor diferente de None.
        campos_identificacion = (
            "identificador_institucional",
            "tipo_documento",
            "numero_documento",
        )

        for campo in campos_identificacion:
            valor = getattr(self, campo)

            if valor is not None:
                if not isinstance(valor, str) or not valor.strip():
                    raise ValueError(
                        f"El campo '{campo}' debe contener texto no vacío "
                        "cuando se proporciona."
                    )
