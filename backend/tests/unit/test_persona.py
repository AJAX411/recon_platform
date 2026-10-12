"""Reglas vigentes de identificación administrativa, sin base de datos."""

import pytest

from recon_platform.personas.dominio.persona import Persona
from recon_platform.personas.dominio.tipo_persona import TipoPersona


def nueva_persona(**cambios: object) -> Persona:
    datos = {
        "tipo_persona": TipoPersona(nombre="ESTUDIANTE"),
        "primer_nombre": "Ana",
        "primer_apellido": "García",
        "tipo_documento": "CC",
        "numero_documento": "00123456",
        "identificador_institucional": "UCC-10234",
    }
    datos.update(cambios)
    return Persona(**datos)


def test_persona_admite_un_nombre_y_un_apellido() -> None:
    persona = nueva_persona()
    assert persona.primer_nombre == "Ana"
    assert persona.primer_apellido == "García"
    assert persona.segundo_nombre is None
    assert persona.segundo_apellido is None


def test_persona_admite_dos_nombres_y_dos_apellidos() -> None:
    persona = nueva_persona(segundo_nombre="Carlos", segundo_apellido="López")
    assert persona.segundo_nombre == "Carlos"
    assert persona.segundo_apellido == "López"


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("primer_nombre", ""),
        ("primer_nombre", "   "),
        ("primer_apellido", ""),
        ("primer_apellido", "   "),
        ("tipo_documento", None),
        ("tipo_documento", ""),
        ("numero_documento", None),
        ("numero_documento", "   "),
    ],
)
def test_persona_rechaza_obligatorios_incompletos(campo: str, valor: object) -> None:
    with pytest.raises(ValueError, match=campo):
        nueva_persona(**{campo: valor})


def test_persona_admite_identificadores_diferentes() -> None:
    persona = nueva_persona()
    assert persona.identificador_institucional == "UCC-10234"
    assert persona.tipo_documento == "CC"
    assert persona.numero_documento == "00123456"


def test_persona_conserva_ceros_y_puntuacion_del_documento() -> None:
    persona = nueva_persona(numero_documento=" 00-123.456 ")
    assert persona.numero_documento == "00-123.456"


@pytest.mark.parametrize("nombre", ["VISITANTE", "DOCENTE", "ADMINISTRATIVO", "PERSONAL_SEGURIDAD", "SERVICIOS_GENERALES"])
def test_identificador_institucional_no_es_obligatorio_sin_regla_explicita(
    nombre: str,
) -> None:
    persona = nueva_persona(
        tipo_persona=TipoPersona(nombre=nombre),
        identificador_institucional=None,
    )
    assert persona.identificador_institucional is None


@pytest.mark.parametrize("identificador", [None, "", "   "])
def test_estudiante_requiere_identificador_institucional(
    identificador: str | None,
) -> None:
    with pytest.raises(ValueError, match="identificador_institucional"):
        nueva_persona(identificador_institucional=identificador)


def test_persona_normaliza_espacios_exteriores() -> None:
    persona = nueva_persona(
        primer_nombre=" Ana ",
        segundo_nombre=" María ",
        primer_apellido=" García ",
        segundo_apellido=" López ",
        tipo_documento=" CC ",
        numero_documento=" 00123456 ",
        identificador_institucional=" UCC-10234 ",
    )
    assert (
        persona.primer_nombre,
        persona.segundo_nombre,
        persona.primer_apellido,
        persona.segundo_apellido,
        persona.tipo_documento,
        persona.numero_documento,
        persona.identificador_institucional,
    ) == ("Ana", "María", "García", "López", "CC", "00123456", "UCC-10234")


def test_identificador_vacio_se_convierte_en_null_para_visitante() -> None:
    persona = nueva_persona(
        tipo_persona=TipoPersona(nombre="VISITANTE"),
        identificador_institucional="   ",
    )
    assert persona.identificador_institucional is None


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("identificador_institucional", 12345),
        ("tipo_documento", 12345),
        ("numero_documento", 12345),
        ("segundo_nombre", " "),
        ("segundo_apellido", " "),
    ],
)
def test_persona_rechaza_texto_invalido(campo: str, valor: object) -> None:
    with pytest.raises(ValueError, match=campo):
        nueva_persona(**{campo: valor})


@pytest.mark.parametrize(
    ("campo", "limite"),
    [
        ("primer_nombre", 100),
        ("segundo_nombre", 100),
        ("primer_apellido", 100),
        ("segundo_apellido", 100),
        ("identificador_institucional", 50),
        ("tipo_documento", 20),
        ("numero_documento", 30),
    ],
)
def test_persona_rechaza_valores_superiores_al_limite(
    campo: str, limite: int
) -> None:
    with pytest.raises(ValueError, match=campo):
        nueva_persona(**{campo: "X" * (limite + 1)})


def test_persona_tiene_tipo_principal() -> None:
    tipo = TipoPersona(nombre="DOCENTE")
    persona = nueva_persona(tipo_persona=tipo)
    assert persona.tipo_persona is tipo


def test_persona_rechaza_tipo_principal_nulo() -> None:
    with pytest.raises(ValueError, match="TipoPersona"):
        nueva_persona(tipo_persona=None)


def test_persona_inicia_activa() -> None:
    assert nueva_persona().estado == "ACTIVO"


def test_persona_admite_estado_inactivo() -> None:
    assert nueva_persona(estado="INACTIVO").estado == "INACTIVO"


@pytest.mark.parametrize("estado", ["", "SUSPENDIDO"])
def test_persona_rechaza_estados_desconocidos(estado: str) -> None:
    with pytest.raises(ValueError, match="estado"):
        nueva_persona(estado=estado)
