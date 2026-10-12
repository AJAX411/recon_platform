"""Pruebas unitarias de la clasificación TipoPersona."""

import pytest

from recon_platform.personas.dominio.tipo_persona import (
    TIPOS_PERSONA_INICIALES,
    TipoPersona,
)


@pytest.mark.parametrize(
    "nombre",
    sorted(TIPOS_PERSONA_INICIALES),
)
def test_tipo_persona_acepta_catalogo_inicial(nombre: str) -> None:
    """Permite las seis clasificaciones del prototipo."""

    tipo = TipoPersona(nombre=nombre)

    assert tipo.nombre == nombre


@pytest.mark.parametrize(
    "nombre",
    [
        "",
        "ESTUDIANTES",
        "INVITADO",
    ],
)
def test_tipo_persona_rechaza_clasificaciones_desconocidas(
    nombre: str,
) -> None:
    """Rechaza valores que no pertenecen al catálogo inicial."""

    with pytest.raises(ValueError, match="catálogo permitido"):
        TipoPersona(nombre=nombre)


def test_tipo_persona_admite_descripcion() -> None:
    """Permite agregar una descripción a la clasificación."""

    tipo = TipoPersona(
        nombre="DOCENTE",
        descripcion="Personal docente de la institución.",
    )

    assert tipo.descripcion == "Personal docente de la institución."


@pytest.mark.parametrize(
    "descripcion",
    ["", "   "],
)
def test_tipo_persona_rechaza_descripcion_vacia(
    descripcion: str,
) -> None:
    """La descripción no puede estar vacía si se proporciona."""

    with pytest.raises(ValueError, match="descripción"):
        TipoPersona(
            nombre="ESTUDIANTE",
            descripcion=descripcion,
        )


def test_tipo_persona_inicia_activo() -> None:
    """Comprueba el estado inicial propuesto."""

    tipo = TipoPersona(nombre="ESTUDIANTE")

    assert tipo.estado == "ACTIVO"


def test_tipo_persona_admite_estado_inactivo() -> None:
    """Permite representar una clasificación inactiva."""

    tipo = TipoPersona(
        nombre="VISITANTE",
        estado="INACTIVO",
    )

    assert tipo.estado == "INACTIVO"


@pytest.mark.parametrize(
    "estado",
    ["", "SUSPENDIDO"],
)
def test_tipo_persona_rechaza_estados_desconocidos(
    estado: str,
) -> None:
    """No permite estados fuera del catálogo inicial."""

    with pytest.raises(ValueError, match="ACTIVO o INACTIVO"):
        TipoPersona(
            nombre="DOCENTE",
            estado=estado,
        )
