"""Reglas de identificación administrativa de una Persona."""

from dataclasses import dataclass
from datetime import datetime

from recon_platform.personas.tipo_persona import TipoPersona

ESTADOS_PERSONA = frozenset({"ACTIVO", "INACTIVO"})


def _texto_obligatorio(valor: object, campo: str, longitud: int) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"El campo '{campo}' es obligatorio y no puede estar vacío.")
    normalizado = valor.strip()
    if len(normalizado) > longitud:
        raise ValueError(f"El campo '{campo}' supera {longitud} caracteres.")
    return normalizado


def _texto_opcional(valor: object, campo: str, longitud: int) -> str | None:
    if valor is None:
        return None
    return _texto_obligatorio(valor, campo, longitud)


@dataclass(kw_only=True, slots=True)
class Persona:
    """Representa a un individuo, independientemente de su cuenta web o biometría."""

    primer_nombre: str
    primer_apellido: str
    tipo_persona: TipoPersona
    tipo_documento: str
    numero_documento: str
    estado: str = "ACTIVO"
    segundo_nombre: str | None = None
    segundo_apellido: str | None = None
    identificador_institucional: str | None = None
    id_persona: int | None = None
    fecha_creacion: datetime | None = None
    fecha_actualizacion: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.tipo_persona, TipoPersona):
            raise ValueError("La Persona debe tener un TipoPersona válido.")
        if not isinstance(self.estado, str) or self.estado not in ESTADOS_PERSONA:
            raise ValueError("El estado de Persona debe ser ACTIVO o INACTIVO.")
        if self.id_persona is not None and (
            not isinstance(self.id_persona, int) or self.id_persona <= 0
        ):
            raise ValueError("id_persona debe ser un entero positivo.")

        self.primer_nombre = _texto_obligatorio(self.primer_nombre, "primer_nombre", 100)
        self.primer_apellido = _texto_obligatorio(
            self.primer_apellido, "primer_apellido", 100
        )
        self.segundo_nombre = _texto_opcional(self.segundo_nombre, "segundo_nombre", 100)
        self.segundo_apellido = _texto_opcional(
            self.segundo_apellido, "segundo_apellido", 100
        )
        self.tipo_documento = _texto_obligatorio(
            self.tipo_documento, "tipo_documento", 20
        )
        self.numero_documento = _texto_obligatorio(
            self.numero_documento, "numero_documento", 30
        )

        identificador = self.identificador_institucional
        if isinstance(identificador, str) and not identificador.strip():
            identificador = None
        self.identificador_institucional = _texto_opcional(
            identificador, "identificador_institucional", 50
        )
        if (
            self.tipo_persona.nombre == "ESTUDIANTE"
            and self.identificador_institucional is None
        ):
            raise ValueError("El identificador_institucional es obligatorio para ESTUDIANTE.")
