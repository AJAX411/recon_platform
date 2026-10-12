"""Casos de uso con dobles en memoria; no conectan a bases de datos."""

import pytest

from recon_platform.personas.aplicacion.casos_de_uso import (
    ConsultarPersona,
    PersonaDuplicada,
    RegistrarPersona,
    TipoPersonaNoExiste,
)
from recon_platform.personas.dominio.persona import Persona
from recon_platform.personas.dominio.tipo_persona import TipoPersona


class RepositorioFalso:
    def __init__(self) -> None:
        self.existentes: list[Persona] = []
        self.pendiente: Persona | None = None

    def existe_documento(self, tipo: str, numero: str) -> bool:
        return any(
            p.tipo_documento == tipo and p.numero_documento == numero
            for p in self.existentes
        )

    def existe_identificador_institucional(self, identificador: str) -> bool:
        return any(
            p.identificador_institucional == identificador for p in self.existentes
        )

    def agregar(self, persona: Persona) -> Persona:
        self.pendiente = persona
        return persona

    def obtener_por_id(self, id_persona: int) -> Persona | None:
        return next((p for p in self.existentes if p.id_persona == id_persona), None)


class TiposFalsos:
    def __init__(self, *nombres: str) -> None:
        self.tipos = {
            nombre: TipoPersona(nombre=nombre, id_tipo_persona=indice)
            for indice, nombre in enumerate(nombres, start=1)
        }

    def obtener_por_nombre(self, nombre: str) -> TipoPersona | None:
        return self.tipos.get(nombre)


class UnidadTrabajoFalsa:
    def __init__(self, personas: RepositorioFalso) -> None:
        self.personas = personas
        self.confirmaciones = 0
        self.reversiones = 0

    def confirmar(self) -> None:
        self.confirmaciones += 1
        if self.personas.pendiente is not None:
            self.personas.pendiente.id_persona = len(self.personas.existentes) + 1
            self.personas.existentes.append(self.personas.pendiente)
            self.personas.pendiente = None

    def revertir(self) -> None:
        self.reversiones += 1
        self.personas.pendiente = None


def nueva_persona(*, documento: str = "00123", identificador: str | None = "UCC-1") -> Persona:
    return Persona(
        primer_nombre="Ana",
        primer_apellido="García",
        tipo_persona=TipoPersona(nombre="ESTUDIANTE"),
        tipo_documento="CC",
        numero_documento=documento,
        identificador_institucional=identificador,
    )


def test_registrar_y_consultar_persona() -> None:
    personas = RepositorioFalso()
    tipos = TiposFalsos("ESTUDIANTE")
    unidad = UnidadTrabajoFalsa(personas)

    guardada = RegistrarPersona(personas, tipos, unidad).ejecutar(nueva_persona())

    assert guardada.id_persona == 1
    assert guardada.tipo_persona.id_tipo_persona == 1
    assert ConsultarPersona(personas).ejecutar(1) is guardada
    assert ConsultarPersona(personas).ejecutar(2) is None
    assert unidad.confirmaciones == 1


def test_registro_sin_tipo_persistido_revierte() -> None:
    personas = RepositorioFalso()
    unidad = UnidadTrabajoFalsa(personas)
    with pytest.raises(TipoPersonaNoExiste):
        RegistrarPersona(personas, TiposFalsos(), unidad).ejecutar(nueva_persona())
    assert unidad.confirmaciones == 0
    assert unidad.reversiones == 1
    assert personas.existentes == []


@pytest.mark.parametrize(
    "cambio",
    [
        {"estado": "INACTIVO"},
        {"id_persona": 7},
    ],
)
def test_registro_no_acepta_estado_o_id_preasignado(cambio: dict[str, object]) -> None:
    personas = RepositorioFalso()
    unidad = UnidadTrabajoFalsa(personas)
    persona = nueva_persona()
    for campo, valor in cambio.items():
        setattr(persona, campo, valor)
    with pytest.raises(ValueError):
        RegistrarPersona(personas, TiposFalsos("ESTUDIANTE"), unidad).ejecutar(persona)
    assert personas.existentes == []
    assert unidad.confirmaciones == 0


@pytest.mark.parametrize("duplicado", ["documento", "institucional"])
def test_registro_duplicado_no_confirma(duplicado: str) -> None:
    personas = RepositorioFalso()
    tipos = TiposFalsos("ESTUDIANTE")
    unidad = UnidadTrabajoFalsa(personas)
    caso = RegistrarPersona(personas, tipos, unidad)
    caso.ejecutar(nueva_persona())

    candidato = (
        nueva_persona(identificador="UCC-2")
        if duplicado == "documento"
        else nueva_persona(documento="00999")
    )
    with pytest.raises(PersonaDuplicada):
        caso.ejecutar(candidato)
    assert len(personas.existentes) == 1
    assert unidad.confirmaciones == 1
    assert unidad.reversiones == 1


def test_error_de_repositorio_revierte_sin_confirmar() -> None:
    class RepositorioConFallo(RepositorioFalso):
        def agregar(self, persona: Persona) -> Persona:
            self.pendiente = persona
            raise RuntimeError("Fallo controlado")

    personas = RepositorioConFallo()
    unidad = UnidadTrabajoFalsa(personas)
    with pytest.raises(RuntimeError, match="Fallo controlado"):
        RegistrarPersona(personas, TiposFalsos("ESTUDIANTE"), unidad).ejecutar(
            nueva_persona()
        )
    assert personas.pendiente is None
    assert personas.existentes == []
    assert unidad.reversiones == 1


@pytest.mark.parametrize("id_persona", [0, -1, "1", None])
def test_consulta_exige_id_interno_positivo(id_persona: object) -> None:
    with pytest.raises(ValueError, match="id_persona"):
        ConsultarPersona(RepositorioFalso()).ejecutar(id_persona)
