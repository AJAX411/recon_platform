"""Pruebas unitarias de las reglas iniciales de Persona."""

import pytest

from recon_platform.personas.dominio.persona import Persona
from recon_platform.personas.dominio.tipo_persona import TipoPersona


def test_persona_admite_un_nombre_y_un_apellido() -> None:
    """Los segundos nombres y apellidos pueden omitirse."""

    persona = Persona(
        tipo_persona=TipoPersona(nombre="ESTUDIANTE"),
        primer_nombre="Ana",
        primer_apellido="García",
    )

    assert persona.primer_nombre == "Ana"
    assert persona.primer_apellido == "García"
    assert persona.segundo_nombre is None
    assert persona.segundo_apellido is None


def test_persona_admite_dos_nombres_y_dos_apellidos() -> None:
    """La Persona puede tener segundos nombres y apellidos."""

    persona = Persona(
        tipo_persona=TipoPersona(nombre="ESTUDIANTE"),
        primer_nombre="Juan",
        segundo_nombre="Carlos",
        primer_apellido="Pérez",
        segundo_apellido="López",
    )

    assert persona.segundo_nombre == "Carlos"
    assert persona.segundo_apellido == "López"


@pytest.mark.parametrize(
    ("primer_nombre", "primer_apellido"),
    [
        ("", "García"),
        ("   ", "García"),
        ("Ana", ""),
        ("Ana", "   "),
    ],
)
def test_persona_rechaza_campos_obligatorios_vacios(
    primer_nombre: str,
    primer_apellido: str,
) -> None:
    """No se permiten valores vacíos en los nombres obligatorios."""

    with pytest.raises(ValueError, match="obligatorio"):
        Persona(
            tipo_persona=TipoPersona(nombre="ESTUDIANTE"),
            primer_nombre=primer_nombre,
            primer_apellido=primer_apellido,
        )


def test_persona_admite_identificadores_diferentes() -> None:
    """El identificador institucional no es el documento de identidad."""

    persona = Persona(
        tipo_persona=TipoPersona(nombre="ESTUDIANTE"),
        primer_nombre="Laura",
        primer_apellido="Martínez",
        identificador_institucional="UCC-10234",
        tipo_documento="CC",
        numero_documento="123456789",
    )

    assert persona.identificador_institucional == "UCC-10234"
    assert persona.tipo_documento == "CC"
    assert persona.numero_documento == "123456789"


def test_persona_admite_identificadores_opcionales() -> None:
    """Los identificadores pueden omitirse según el modelo lógico actual."""

    persona = Persona(
        tipo_persona=TipoPersona(nombre="ESTUDIANTE"),
        primer_nombre="Andrés",
        primer_apellido="Rojas",
    )

    assert persona.identificador_institucional is None
    assert persona.tipo_documento is None
    assert persona.numero_documento is None


def test_persona_conserva_ceros_iniciales_del_documento() -> None:
    """El documento se representa como texto, no como número entero."""

    persona = Persona(
        tipo_persona=TipoPersona(nombre="ESTUDIANTE"),
        primer_nombre="Camila",
        primer_apellido="Gómez",
        tipo_documento="TI",
        numero_documento="00123456",
    )

    assert persona.numero_documento == "00123456"


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("identificador_institucional", ""),
        ("identificador_institucional", "   "),
        ("identificador_institucional", 12345),
        ("tipo_documento", ""),
        ("tipo_documento", "   "),
        ("tipo_documento", 12345),
        ("numero_documento", ""),
        ("numero_documento", "   "),
        ("numero_documento", 12345),
    ],
)
def test_persona_rechaza_identificadores_invalidos(
    campo: str,
    valor: object,
) -> None:
    """Los identificadores proporcionados deben contener texto válido."""

    datos_identificacion = {campo: valor}

    with pytest.raises(ValueError, match=campo):
        Persona(
            tipo_persona=TipoPersona(nombre="ESTUDIANTE"),
            primer_nombre="Laura",
            primer_apellido="Martínez",
            **datos_identificacion,
        )


def test_persona_tiene_tipo_principal() -> None:
    """Cada Persona debe estar asociada a una clasificación."""

    tipo = TipoPersona(nombre="DOCENTE")

    persona = Persona(
        primer_nombre="Carlos",
        primer_apellido="Rojas",
        tipo_persona=tipo,
    )

    assert persona.tipo_persona is tipo
    assert persona.tipo_persona.nombre == "DOCENTE"


def test_persona_rechaza_tipo_principal_nulo() -> None:
    """No se permite una Persona sin clasificación principal."""

    with pytest.raises(ValueError, match="TipoPersona"):
        Persona(
            primer_nombre="Ana",
            primer_apellido="García",
            tipo_persona=None,  # type: ignore[arg-type]
        )
