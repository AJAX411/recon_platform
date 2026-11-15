"""Casos de uso con dobles en memoria; no conectan a bases de datos."""

from copy import deepcopy
from typing import cast

import pytest

from recon_platform.personas.servicios.personas import (
    ConsultarPersona,
    ActorPersonas,
    AdministrarPersonas,
    PersonaNoExiste,
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
        self.eventos: list[tuple[int, str, int]] = []
        self.eventos_pendientes: list[tuple[int, str, int]] = []
        self.fallar_auditoria = False

    def existe_documento(self, tipo: str, numero: str, excluir_id: int | None = None) -> bool:
        return any(
            p.tipo_documento == tipo and p.numero_documento == numero
            and (excluir_id is None or p.id_persona != excluir_id)
            for p in self.existentes
        )

    def existe_identificador_institucional(self, identificador: str,
                                           excluir_id: int | None = None) -> bool:
        return any(
            p.identificador_institucional == identificador
            and (excluir_id is None or p.id_persona != excluir_id)
            for p in self.existentes
        )

    def agregar(self, persona: Persona) -> Persona:
        persona.id_persona = len(self.existentes) + 1
        self.pendiente = persona
        return persona

    def obtener_por_id(self, id_persona: int) -> Persona | None:
        return next((p for p in self.existentes if p.id_persona == id_persona), None)

    def listar(self, *, limite: int, desplazamiento: int,
               filtros: dict[str, str]) -> list[Persona]:
        personas = [persona for persona in self.existentes if all(
            (persona.tipo_persona.nombre if campo == "tipo_persona" else getattr(persona, campo))
            == valor for campo, valor in filtros.items()
        )]
        return personas[desplazamiento:desplazamiento + limite]

    def actualizar(self, persona: Persona) -> Persona:
        if persona.id_persona is None or self.obtener_por_id(persona.id_persona) is None:
            raise PersonaNoExiste("La Persona no existe.")
        self.pendiente = persona
        return persona

    def auditar(self, *, actor_id: int, accion: str, id_persona: int) -> None:
        if self.fallar_auditoria:
            raise RuntimeError("Fallo ficticio de auditoría")
        self.eventos_pendientes.append((actor_id, accion, id_persona))


class TiposFalsos:
    def __init__(self, *nombres: str) -> None:
        self.tipos = {
            nombre: TipoPersona(nombre=nombre, id_tipo_persona=indice)
            for indice, nombre in enumerate(nombres, start=1)
        }

    def obtener_por_nombre(self, nombre: str) -> TipoPersona | None:
        return self.tipos.get(nombre)

    def listar(self) -> list[TipoPersona]:
        return list(self.tipos.values())


class UnidadTrabajoFalsa:
    def __init__(self, personas: RepositorioFalso) -> None:
        self.personas = personas
        self.confirmaciones = 0
        self.reversiones = 0
        self.estado = deepcopy((personas.existentes, personas.eventos))

    def confirmar(self) -> None:
        self.confirmaciones += 1
        if self.personas.pendiente is not None:
            pendiente = self.personas.pendiente
            assert pendiente.id_persona is not None
            indice = next((i for i, persona in enumerate(self.personas.existentes)
                           if persona.id_persona == pendiente.id_persona), None)
            if indice is None:
                self.personas.existentes.append(pendiente)
            else:
                self.personas.existentes[indice] = pendiente
            self.personas.pendiente = None
        self.personas.eventos.extend(self.personas.eventos_pendientes)
        self.personas.eventos_pendientes.clear()
        self.estado = deepcopy((self.personas.existentes, self.personas.eventos))

    def revertir(self) -> None:
        self.reversiones += 1
        self.personas.pendiente = None
        self.personas.eventos_pendientes.clear()
        self.personas.existentes, self.personas.eventos = deepcopy(self.estado)


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
        # Entrada inválida deliberada: cast conserva el mismo valor en ejecución.
        ConsultarPersona(RepositorioFalso()).ejecutar(cast(int, id_persona))


def test_dobles_personas_listan_filtran_excluyen_id_y_actualizan_con_auditoria():
    personas = RepositorioFalso()
    tipos = TiposFalsos("ESTUDIANTE", "VISITANTE")
    unidad = UnidadTrabajoFalsa(personas)
    caso = AdministrarPersonas(personas, tipos, unidad)
    actor = ActorPersonas(1, "SUPERADMIN")
    primera = caso.registrar(actor=actor, persona=nueva_persona())
    segunda = caso.registrar(actor=actor, persona=nueva_persona(
        documento="SEGUNDA", identificador="UCC-2"))
    assert primera.id_persona is not None and segunda.id_persona is not None
    assert [tipo.nombre for tipo in caso.listar_tipos(actor=actor)] == ["ESTUDIANTE", "VISITANTE"]
    assert caso.listar(actor=actor, limite=1, desplazamiento=1) == [segunda]
    assert caso.listar(actor=actor, filtros={"numero_documento": "00123",
                                          "tipo_persona": "ESTUDIANTE"}) == [primera]
    assert not personas.existe_documento("CC", "00123", excluir_id=primera.id_persona)
    assert personas.existe_documento("CC", "00123", excluir_id=segunda.id_persona)
    assert not personas.existe_identificador_institucional("UCC-1", excluir_id=primera.id_persona)
    assert personas.existe_identificador_institucional("UCC-1", excluir_id=segunda.id_persona)
    actualizada = caso.actualizar(actor=actor, id_persona=primera.id_persona,
                                  datos={"primer_nombre": "Nuevo"})
    assert caso.consultar(actor=actor, id_persona=primera.id_persona).primer_nombre == "Nuevo"
    assert actualizada.id_persona == primera.id_persona
    assert personas.eventos[-1] == (1, "ACTUALIZAR_PERSONA", primera.id_persona)
    assert unidad.confirmaciones == 3


def test_doble_personas_revierte_estado_y_auditoria_si_falla_su_registro():
    personas = RepositorioFalso()
    unidad = UnidadTrabajoFalsa(personas)
    caso = AdministrarPersonas(personas, TiposFalsos("ESTUDIANTE"), unidad)
    actor = ActorPersonas(1, "SUPERADMIN")
    registrada = caso.registrar(actor=actor, persona=nueva_persona())
    assert registrada.id_persona is not None
    eventos_antes = list(personas.eventos)
    personas.fallar_auditoria = True
    with pytest.raises(RuntimeError, match="auditoría"):
        caso.cambiar_estado(actor=actor, id_persona=registrada.id_persona, estado="INACTIVO")
    assert caso.consultar(actor=actor, id_persona=registrada.id_persona).estado == "ACTIVO"
    assert personas.eventos == eventos_antes
    assert personas.pendiente is None and personas.eventos_pendientes == []
    assert unidad.reversiones == 1
