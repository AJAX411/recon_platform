"""Catálogo de nuevas asignaciones; no restringe la lectura del legado."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TipoDocumento:
    codigo: str
    nombre: str
    habilitado_para_altas: bool = True


TIPOS_DOCUMENTO = (
    TipoDocumento("CC", "Cédula de ciudadanía"),
    TipoDocumento("TI", "Tarjeta de identidad"),
    TipoDocumento("CE", "Cédula de extranjería"),
    TipoDocumento("PA", "Pasaporte"),
    TipoDocumento("PPT", "Permiso por Protección Temporal"),
    TipoDocumento("RC", "Registro civil de nacimiento"),
)


def catalogo_tipos_documento() -> tuple[TipoDocumento, ...]:
    return TIPOS_DOCUMENTO


def tipo_documento_habilitado(codigo: str) -> bool:
    return any(tipo.codigo == codigo and tipo.habilitado_para_altas
               for tipo in TIPOS_DOCUMENTO)
