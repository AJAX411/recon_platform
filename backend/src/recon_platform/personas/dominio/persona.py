"""Representación inicial de una Persona en el dominio.

Esta versión incorpora nombres, apellidos e identificadores.

La clase todavía no define el modelo físico de MySQL ni
las relaciones definitivas con otras entidades del sistema.
"""

from dataclasses import dataclass


@dataclass(kw_only=True, slots=True)
class Persona:
    """Representa los datos iniciales de identificación de una persona."""

    # Datos personales obligatorios.
    primer_nombre: str
    primer_apellido: str

    # Datos personales opcionales.
    segundo_nombre: str | None = None
    segundo_apellido: str | None = None

    # Identificación institucional.
    identificador_institucional: str | None = None

    # Documento de identidad.
    tipo_documento: str | None = None
    numero_documento: str | None = None

    def __post_init__(self) -> None:
        """Comprueba que los campos obligatorios tengan contenido."""

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
